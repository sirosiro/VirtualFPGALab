import time
import struct
from multiprocessing import shared_memory

SHM_NAME = "vfpga_reg"
SHM_SIZE = 1024  # 1KB for registers

def main():
    print(f"[Python] Starting Virtual Logic Controller...")
    
    # Create shared memory
    try:
        # If it already exists, unlink it first
        try:
            temp_shm = shared_memory.SharedMemory(name=SHM_NAME)
            temp_shm.close()
            temp_shm.unlink()
            print(f"[Python] Cleaned up existing shared memory '{SHM_NAME}'")
        except FileNotFoundError:
            pass

        shm = shared_memory.SharedMemory(name=SHM_NAME, create=True, size=SHM_SIZE)
        print(f"[Python] Created shared memory '{SHM_NAME}' (Size: {SHM_SIZE} bytes)")

        # Write a dummy register value at offset 0 (4 bytes)
        # 0x12345678 in little-endian
        val = 0x12345678
        shm.buf[0:4] = struct.pack("<I", val)
        print(f"[Python] Wrote value 0x{val:08X} to offset 0x00")

        print("[Python] Controller is running. Press Ctrl+C to stop.")
        last_val = 0
        while True:
            # Read value at offset 4 (4 bytes)
            current_val = struct.unpack("<I", shm.buf[4:8])[0]
            if current_val != last_val:
                print(f"[Python] Register Change Detected at offset 0x04: 0x{current_val:08X}")
                last_val = current_val
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n[Python] Stopping Controller...")
    finally:
        shm.close()
        shm.unlink()
        print("[Python] Shared memory cleaned up.")

if __name__ == "__main__":
    main()
