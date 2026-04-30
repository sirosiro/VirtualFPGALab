import time
import sys
import re
import os
import mmap
import glob
import socket
import threading
import select

# プロジェクトルートの動的取得 (src/controller/vlogic_controller.py から見て 2つ上の階層)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
SHM_NAME = "vfpga_reg"

def get_shm_info_from_dts(dts_path):
    regions = []
    try:
        if not os.path.exists(dts_path):
            return regions
        with open(dts_path, 'r') as f:
            content = f.read()
        
        matches = re.finditer(r'([a-zA-Z0-9_@]+)\s*\{([^}]+)\}', content)
        for match in matches:
            raw_name = match.group(1).strip()
            name = raw_name.split('@')[0]
            body = match.group(2)
            
            comp_match = re.search(r'compatible\s*=\s*"([^"]+)"', body)
            is_uio = False
            if comp_match and 'generic-uio' in comp_match.group(1):
                is_uio = True
            
            reg_match = re.search(r'reg\s*=\s*<[^ ]+\s+([^>]+)>', body)
            if reg_match:
                try:
                    size = int(reg_match.group(1).strip(), 0)
                    regions.append({'name': name, 'size': size, 'is_uio': is_uio})
                except:
                    continue
    except Exception as e:
        print(f"[Python] Error parsing DTS: {e}")
    return regions


def uart_bridge_thread(pts_path, port):
    print(f"[Python] Starting UART bridge for {pts_path} on port {port}...")
    
    pts_fd = -1
    # 起動直後の極小のレースコンディションを回避するため、数回リトライする
    for i in range(10):
        try:
            pts_fd = os.open(pts_path, os.O_RDWR | os.O_NOCTTY)
            break
        except Exception as e:
            if i == 9:
                print(f"[Python] UART Bridge Final Error: {e}")
                return
            time.sleep(0.2)

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(('0.0.0.0', port))
    server_sock.listen(1)
    
    while True:
        try:
            conn, addr = server_sock.accept()
            print(f"[Python] UART {port} connected from {addr}")
            while True:
                r, w, e = select.select([pts_fd, conn], [], [])
                if pts_fd in r:
                    data = os.read(pts_fd, 1024)
                    if not data: break
                    conn.sendall(data)
                if conn in r:
                    data = conn.recv(1024)
                    if not data: break
                    os.write(pts_fd, data)
            conn.close()
        except Exception:
            break

def update_uart_map(active_bridges):
    import json
    try:
        mapping = {os.path.basename(f): port for f, port in active_bridges.items()}
        map_path = os.path.join(PROJECT_ROOT, "dashboard/data/uart_map.json")
        with open(map_path, "w") as f:
            json.dump(mapping, f)
    except Exception as e:
        print(f"[Python] Error updating UART map: {e}")

def uart_discovery_thread():
    active_bridges = {}
    base_port = 2000
    print("[Python] UART Discovery thread started.")
    while True:
        glob_pattern = os.path.join(PROJECT_ROOT, "dashboard/data/vfpga_uart_*")
        files = glob.glob(glob_pattern)
        changed = False
        for f in files:
            if f not in active_bridges:
                try:
                    with open(f, 'r') as f_ptr:
                        pts_path = f_ptr.read().strip()
                    port = base_port + len(active_bridges)
                    t = threading.Thread(target=uart_bridge_thread, args=(pts_path, port), daemon=True)
                    t.start()
                    active_bridges[f] = port
                    print(f"[Python] UART Found: {f} -> {pts_path} (TCP Port {port})")
                    changed = True
                except Exception as e:
                    print(f"[Python] Error starting bridge for {f}: {e}")
        
        if changed:
            update_uart_map(active_bridges)
        time.sleep(1)

def main():
    if len(sys.argv) < 2:
        print("Usage: vlogic_controller.py <dts_path>")
        sys.exit(1)
        
    # Start discovery
    t = threading.Thread(target=uart_discovery_thread, daemon=True)
    t.start()

    dts_path = sys.argv[1]
    regions = get_shm_info_from_dts(dts_path)
    
    # ジェネレータ側のロジックと合わせる
    uio = next((r for r in regions if r.get('is_uio')), None)
    board_name = uio['name'] if uio else "vfpga_reg"
    board_size = uio['size'] if uio else (regions[0]['size'] if regions else 1024)

    print(f"[Python] Starting Generic Virtual Logic Controller...")
    print(f"[Python] Using DTS: {dts_path}")
    
    path = f"/tmp/{board_name}"
    print(f"[Python] Creating SHM file: {path}, Size: {board_size}")
    
    shm = None
    try:
        # Create or open the file
        fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o666)
        os.ftruncate(fd, board_size)
        
        # Mmap it
        shm = mmap.mmap(fd, board_size)
        os.close(fd) # The mapping survives the close of the FD

        print("[Python] Backend is ready. Logic is handled by Verilator/RTL.")
        print("[Python] Press Ctrl+C to stop.")
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n[Python] Stopping Controller...")
    finally:
        for shm in shm_objects:
            shm.close()
        # The files in /tmp can stay or be cleaned up by start_lab.sh

if __name__ == "__main__":
    main()
