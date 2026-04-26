import struct
import re
from flask import Flask, jsonify, render_template_string
from flask_cors import CORS
from multiprocessing import shared_memory

app = Flask(__name__)
CORS(app)

def get_shm_config_from_dts(dts_path):
    config = {
        "shm_name": "vfpga_reg",
        "shm_size": 1024,
        "registers": []
    }
    try:
        with open(dts_path, 'r') as f:
            content = f.read()
        
        # Extract SHM name and size
        match = re.search(r'([a-zA-Z0-9_]+)@[0-9a-f]+\s*\{([^}]+)\}', content)
        if match:
            config["shm_name"] = match.group(1).strip()
            body = match.group(2)
            reg_match = re.search(r'reg\s*=\s*<[^ ]+\s+([^>]+)>', body)
            if reg_match:
                config["shm_size"] = int(reg_match.group(1).strip(), 0)
            
            # Extract register names and offsets
            if 'registers =' in body:
                reg_list_match = re.search(r'registers\s*=\s*([^;]+);', body)
                if reg_list_match:
                    reg_list = reg_list_match.group(1).split(',')
                    for r in reg_list:
                        r = r.strip().strip('"')
                        if '@' in r:
                            name, offset = r.split('@')
                            config["registers"].append({
                                "name": name.strip(),
                                "offset": int(offset.strip(), 0)
                            })
    except Exception as e:
        print(f"[Dashboard] Error parsing DTS: {e}")
    return config

DTS_PATH = "tests/vfpga_config.dts"
CONFIG = get_shm_config_from_dts(DTS_PATH)

def get_shm():
    try:
        return shared_memory.SharedMemory(name=CONFIG["shm_name"])
    except FileNotFoundError:
        return None

@app.route('/api/registers')
def get_registers():
    shm = get_shm()
    if not shm:
        return jsonify({"error": f"SHM '{CONFIG['shm_name']}' not found"}), 404
    
    registers = []
    # Use registers defined in DTS
    for reg in CONFIG["registers"]:
        offset = reg["offset"]
        if offset + 4 <= CONFIG["shm_size"]:
            val = struct.unpack("<I", shm.buf[offset:offset+4])[0]
            registers.append({
                "address": f"0x{offset:02X}",
                "value": f"0x{val:08X}",
                "decimal": val,
                "name": reg["name"]
            })
    
    shm.close()
    return jsonify(registers)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VirtualFPGALab Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&family=JetBrains+Mono&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0a0e14;
            --card-bg: rgba(255, 255, 255, 0.05);
            --accent-color: #00d2ff;
            --text-primary: #e6edf3;
            --text-secondary: #8b949e;
        }
        body {
            font-family: 'Outfit', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-primary);
            margin: 0;
            padding: 2rem;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        h1 {
            font-weight: 600;
            background: linear-gradient(90deg, #00d2ff 0%, #3a7bd5 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 2rem;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1.5rem;
            width: 100%;
            max-width: 1200px;
        }
        .card {
            background: var(--card-bg);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            padding: 1.5rem;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.3);
            border-color: var(--accent-color);
        }
        .reg-name {
            font-size: 0.85rem;
            color: var(--text-secondary);
            margin-bottom: 0.5rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .reg-value {
            font-family: 'JetBrains Mono', monospace;
            font-size: 1.8rem;
            color: var(--accent-color);
        }
        .reg-addr {
            font-size: 0.75rem;
            color: var(--text-secondary);
            margin-top: 1rem;
            text-align: right;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            padding-top: 0.5rem;
        }
        .status {
            margin-top: 2rem;
            font-size: 0.9rem;
            color: var(--text-secondary);
        }
    </style>
</head>
<body>
    <h1>VirtualFPGALab Live Dashboard</h1>
    <div class="grid" id="register-grid">
        <!-- Registers will be injected here -->
    </div>
    <div class="status" id="last-update">Last update: --:--:--</div>

    <script>
        async function updateRegisters() {
            try {
                const response = await fetch('/api/registers');
                if (!response.ok) throw new Error('Backend not ready');
                const data = await response.json();
                const grid = document.getElementById('register-grid');
                grid.innerHTML = '';

                data.forEach(reg => {
                    const card = document.createElement('div');
                    card.className = 'card';
                    card.innerHTML = `
                        <div class="reg-name">${reg.name}</div>
                        <div class="reg-value">${reg.value}</div>
                        <div class="reg-addr">Offset: ${reg.address}</div>
                    `;
                    grid.appendChild(card);
                });

                document.getElementById('last-update').innerText = 'Last update: ' + new Date().toLocaleTimeString();
            } catch (error) {
                document.getElementById('last-update').innerText = 'Status: Disconnected (Wait for backend)';
            }
        }

        setInterval(updateRegisters, 500);
        updateRegisters();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(DASHBOARD_HTML)

if __name__ == '__main__':
    print(f"[Dashboard] Starting on port 8080...")
    print(f"[Dashboard] Monitoring SHM: {CONFIG['shm_name']}")
    app.run(host='0.0.0.0', port=8080)
