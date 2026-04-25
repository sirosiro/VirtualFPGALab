import struct
from flask import Flask, jsonify, render_template_string
from flask_cors import CORS
from multiprocessing import shared_memory
import threading

SHM_NAME = "vfpga_reg"
SHM_SIZE = 1024

app = Flask(__name__)
CORS(app)

def get_shm():
    try:
        return shared_memory.SharedMemory(name=SHM_NAME)
    except FileNotFoundError:
        return None

@app.route('/api/registers')
def get_registers():
    shm = get_shm()
    if not shm:
        return jsonify({"error": "SHM not found"}), 404
    
    registers = []
    # Read first 32 bytes as 8 registers (32-bit each)
    for i in range(8):
        offset = i * 4
        val = struct.unpack("<I", shm.buf[offset:offset+4])[0]
        registers.append({
            "address": f"0x{offset:02X}",
            "value": f"0x{val:08X}",
            "decimal": val,
            "name": get_reg_name(offset)
        })
    
    shm.close()
    return jsonify(registers)

def get_reg_name(offset):
    names = {
        0x00: "Magic ID",
        0x04: "Status / Debug",
        0x10: "RTL Reset",
        0x14: "RTL Enable",
        0x18: "RTL Counter"
    }
    return names.get(offset, f"Reg {offset:02X}")

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
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            width: 100%;
            max-width: 1000px;
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
        }
        .reg-value {
            font-family: 'JetBrains Mono', monospace;
            font-size: 1.5rem;
            color: var(--accent-color);
        }
        .reg-addr {
            font-size: 0.75rem;
            color: var(--text-secondary);
            margin-top: 1rem;
            text-align: right;
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
                const data = await response.json();
                const grid = document.getElementById('register-grid');
                grid.innerHTML = '';

                data.forEach(reg => {
                    const card = document.createElement('div');
                    card.className = 'card';
                    card.innerHTML = `
                        <div class="reg-name">${reg.name}</div>
                        <div class="reg-value">${reg.value}</div>
                        <div class="reg-addr">Addr: ${reg.address}</div>
                    `;
                    grid.appendChild(card);
                });

                document.getElementById('last-update').innerText = 'Last update: ' + new Date().toLocaleTimeString();
            } catch (error) {
                console.error('Failed to fetch registers:', error);
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
    app.run(host='0.0.0.0', port=5000)
