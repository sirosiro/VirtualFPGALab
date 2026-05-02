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
            label_match = re.search(r'label\s*=\s*"([^"]+)"', body)
            is_uio = False
            is_gpio = False
            if comp_match:
                compat = comp_match.group(1)
                if 'generic-uio' in compat:
                    is_uio = True
                elif 'gpio' in compat or 'xlnx,xps-gpio' in compat:
                    is_gpio = True
            # label が /dev/uio で始まるデバイスも UIO として扱う (カスタムIP対応)
            if not is_uio and not is_gpio and label_match and label_match.group(1).startswith('/dev/uio'):
                is_uio = True
            
            reg_match = re.search(r'reg\s*=\s*<([^>]+)>', body)
            if reg_match:
                try:
                    parts = reg_match.group(1).strip().split()
                    base_addr = int(parts[0], 0)
                    size = int(parts[1], 0) if len(parts) >= 2 else 0
                    regions.append({'name': name, 'base_addr': base_addr, 'size': size, 'is_uio': is_uio, 'is_gpio': is_gpio})
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
    # key: uart_file_path -> (pts_path, thread, port)
    active_bridges = {}
    base_port = 2000
    next_port = base_port
    print("[Python] UART Discovery thread started.")
    while True:
        glob_pattern = os.path.join(PROJECT_ROOT, "dashboard/data/vfpga_uart_*")
        files = glob.glob(glob_pattern)
        changed = False
        for f in files:
            try:
                with open(f, 'r') as f_ptr:
                    pts_path = f_ptr.read().strip()
            except Exception:
                continue

            existing = active_bridges.get(f)
            # PTSパスが変わった、またはスレッドが終了していたら再起動
            if existing is None or existing[0] != pts_path or not existing[1].is_alive():
                port = existing[2] if existing else next_port
                if existing is None:
                    next_port += 1
                t = threading.Thread(target=uart_bridge_thread, args=(pts_path, port), daemon=True)
                t.start()
                active_bridges[f] = (pts_path, t, port)
                print(f"[Python] UART Found: {f} -> {pts_path} (TCP Port {port})")
                changed = True

        if changed:
            update_uart_map({f: v[2] for f, v in active_bridges.items()})
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
    
    # ジェネレータ側のロジックと合わせる (gen_vfpga.py と同じ計算)
    uio_gpio_devs = [r for r in regions if r.get('is_uio') or r.get('is_gpio')]
    
    # ボード名: UIO > GPIO > デフォルト
    uio = next((r for r in regions if r.get('is_uio')), None)
    if uio:
        board_name = uio['name']
    else:
        gpio = next((r for r in regions if r.get('is_gpio')), None)
        board_name = gpio['name'] if gpio else "vfpga_reg"
    
    # SHMサイズ: 全UIO/GPIOデバイスの物理アドレス範囲をカバー
    if len(uio_gpio_devs) == 0:
        board_size = 1024
    elif len(uio_gpio_devs) == 1:
        board_size = uio_gpio_devs[0]['size']
    else:
        min_addr = min(d['base_addr'] for d in uio_gpio_devs)
        max_end = max(d['base_addr'] + d['size'] for d in uio_gpio_devs)
        board_size = max_end - min_addr

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
