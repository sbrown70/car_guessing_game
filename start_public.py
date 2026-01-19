#!/usr/bin/env python3
"""
Car Guess Game - Public Access Launcher
Creates a public URL so you can play from anywhere!
"""

import subprocess
import sys
import os
import time
import threading

def start_server():
    """Start the game server."""
    server_path = os.path.join(os.path.dirname(__file__), 'server.py')
    subprocess.run([sys.executable, server_path])

def main():
    print("=" * 60)
    print("    CAR GUESS GAME - Public Access Mode")
    print("=" * 60)
    print()
    print("Starting server...")

    # Start server in background thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    # Wait for server to start
    time.sleep(3)

    # Start ngrok
    try:
        from pyngrok import ngrok

        print("Creating public tunnel...")
        print()

        # Create tunnel
        public_url = ngrok.connect(3000)

        print("=" * 60)
        print("  GAME IS LIVE!")
        print("=" * 60)
        print()
        print(f"  Public URL (play anywhere):")
        print(f"  {public_url}")
        print()
        print(f"  Local URL:")
        print(f"  http://localhost:3000")
        print()
        print("=" * 60)
        print("Share the public URL with friends!")
        print("Press Ctrl+C to stop")
        print("=" * 60)
        print()

        # Keep running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")
            ngrok.disconnect(public_url)

    except ImportError:
        print("Error: pyngrok not installed. Run: pip install pyngrok")
        sys.exit(1)
    except Exception as e:
        print(f"Error starting tunnel: {e}")
        print("\nYou may need to sign up for a free ngrok account:")
        print("1. Go to https://ngrok.com and create free account")
        print("2. Get your auth token from the dashboard")
        print("3. Run: ngrok config add-authtoken YOUR_TOKEN")
        sys.exit(1)

if __name__ == '__main__':
    main()
