#!/usr/bin/env python3
import os
import sys
import socket
import threading
import select

def bridge(pts_path, port):
    print(f"[Bridge] Starting UART bridge for {pts_path} on port {port}...")
    
    # Open the PTS (slave side is handled by Shim, we open master as a regular file if needed, 
    # but here Shim returns master FD, so we actually need to open the SLAVE side to act as the other end)
    try:
        pts_fd = os.open(pts_path, os.O_RDWR | os.O_NOCTTY)
    except Exception as e:
        print(f"[Bridge] Error opening {pts_path}: {e}")
        return

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(('0.0.0.0', port))
    server_sock.listen(1)
    
    print(f"[Bridge] Waiting for TCP connection on port {port}...")
    
    while True:
        conn, addr = server_sock.accept()
        print(f"[Bridge] Accepted connection from {addr}")
        
        try:
            while True:
                # Use select to wait for data on either PTS or Socket
                r, w, e = select.select([pts_fd, conn], [], [])
                
                if pts_fd in r:
                    data = os.read(pts_fd, 1024)
                    if not data: break
                    conn.sendall(data)
                
                if conn in r:
                    data = conn.recv(1024)
                    if not data: break
                    os.write(pts_fd, data)
        except Exception as e:
            print(f"[Bridge] Connection closed: {e}")
        finally:
            conn.close()
            print("[Bridge] Waiting for new connection...")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: uart_bridge.py <pts_path> <port>")
        sys.exit(1)
    
    bridge(sys.argv[1], int(sys.argv[2]))
