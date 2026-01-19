#!/usr/bin/env python3
"""
Car Guess Game - Easy Start Script
Run this to start the game and get the URL for phone access.
"""

import socket
import subprocess
import sys
import os

def get_local_ip():
    """Get the local IP address for network access."""
    try:
        # Connect to a public IP to find local interface
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "localhost"

def main():
    print("=" * 60)
    print("       CAR GUESS GAME - Starting Server")
    print("=" * 60)
    print()

    local_ip = get_local_ip()
    port = 3000

    print("Access the game at:")
    print()
    print(f"  Local:    http://localhost:{port}")
    print(f"  Network:  http://{local_ip}:{port}")
    print()
    print("To play on your phone (same WiFi network):")
    print(f"  Open: http://{local_ip}:{port}")
    print()
    print("=" * 60)
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    print()

    # Start the server
    server_path = os.path.join(os.path.dirname(__file__), 'server.py')
    subprocess.run([sys.executable, server_path])

if __name__ == '__main__':
    main()
