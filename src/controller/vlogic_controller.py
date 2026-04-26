import time
import struct
import sys
import re
from multiprocessing import shared_memory

SHM_NAME = "vfpga_reg"

def get_shm_info_from_dts(dts_path):
    shm_name = "vfpga_reg"
    shm_size = 1024
    try:
        with open(dts_path, 'r') as f:
            content = f.read()
        
        # Find node@addr { ... reg = <... size> ... }
        # Simple extraction for demo
        match = re.search(r'([a-zA-Z0-9_]+)@[0-9a-f]+\s*\{[^}]+reg\s*=\s*<[^ ]+\s+([^>]+)>', content)
        if match:
            shm_name = match.group(1).strip()
            shm_size = int(match.group(2).strip(), 0)
    except Exception as e:
        print(f"[Python] Error parsing DTS: {e}")
    return shm_name, shm_size

def main():
    dts_path = "tests/vfpga_config.dts"
    shm_name, shm_size = get_shm_info_from_dts(dts_path)
    
    print(f"[Python] Starting Generic Virtual Logic Controller...")
    print(f"[Python] Using DTS: {dts_path}")
    print(f"[Python] Detected SHM Name: {shm_name}, Size: {shm_size}")
    
    try:
        # Clean up
        try:
            temp_shm = shared_memory.SharedMemory(name=shm_name)
            temp_shm.unlink()
        except FileNotFoundError:
            pass

        shm = shared_memory.SharedMemory(name=shm_name, create=True, size=shm_size)
        print(f"[Python] Created shared memory '{shm_name}'")

        print("[Python] Backend is ready. Logic is handled by Verilator/RTL.")
        print("[Python] Press Ctrl+C to stop.")
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n[Python] Stopping Controller...")
    finally:
        shm.close()
        shm.unlink()

if __name__ == "__main__":
    main()
