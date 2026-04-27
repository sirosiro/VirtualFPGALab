import time
import struct
import sys
import re
import os
from multiprocessing import shared_memory

SHM_NAME = "vfpga_reg"

def get_shm_info_from_dts(dts_path):
    regions = []
    try:
        with open(dts_path, 'r') as f:
            content = f.read()
        
        # Find all patterns like node@addr { ... reg = <... size> ... }
        matches = re.finditer(r'([a-zA-Z0-9_]+)@[0-9a-f]+\s*\{([^}]+)\}', content)
        for match in matches:
            name = match.group(1).strip()
            body = match.group(2)
            
            # Extract size from reg = <addr size>
            reg_match = re.search(r'reg\s*=\s*<[^ ]+\s+([^>]+)>', body)
            if reg_match:
                size = int(reg_match.group(1).strip(), 0)
                regions.append({'name': name, 'size': size})
    except Exception as e:
        print(f"[Python] Error parsing DTS: {e}")
    return regions

import glob
import socket
import threading
import select

def uart_bridge_thread(pts_path, port):
    print(f"[Python] Starting UART bridge for {pts_path} on port {port}...")
    try:
        pts_fd = os.open(pts_path, os.O_RDWR | os.O_NOCTTY)
    except Exception as e:
        print(f"[Python] UART Bridge Error: {e}")
        return

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

def uart_discovery_thread():
    active_bridges = {}
    base_port = 2000
    print("[Python] UART Discovery thread started.")
    while True:
        files = glob.glob("/tmp/vfpga_uart_*")
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
                except Exception as e:
                    print(f"[Python] Error starting bridge for {f}: {e}")
        time.sleep(1)

def main():
    if len(sys.argv) < 2:
        print("Usage: vlogic_controller.py <dts_path>")
        sys.exit(1)
        
    # Clean up old mapping files
    for f in glob.glob("/tmp/vfpga_uart_*"):
        os.remove(f)

    # Start discovery
    t = threading.Thread(target=uart_discovery_thread, daemon=True)
    t.start()

    dts_path = sys.argv[1]
    regions = get_shm_info_from_dts(dts_path)
    
    print(f"[Python] Starting Generic Virtual Logic Controller...")
    print(f"[Python] Using DTS: {dts_path}")
    
    shm_objects = []
    try:
        for reg in regions:
            name = reg['name']
            size = reg['size']
            print(f"[Python] Creating SHM: {name}, Size: {size}")
            
            # Clean up existing
            try:
                temp_shm = shared_memory.SharedMemory(name=name)
                temp_shm.unlink()
            except FileNotFoundError:
                pass

            shm = shared_memory.SharedMemory(name=name, create=True, size=size)
            shm_objects.append(shm)

        print("[Python] Backend is ready. Logic is handled by Verilator/RTL.")
        print("[Python] Press Ctrl+C to stop.")
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n[Python] Stopping Controller...")
    finally:
        for shm in shm_objects:
            shm.close()
            shm.unlink()

if __name__ == "__main__":
    main()
