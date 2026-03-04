#!/usr/bin/env python3
"""
Script to run the Home Automation web application on port 8080
"""

import sys
import os
import uvicorn

def find_available_port(start_port=8000, max_attempts=10):
    """Find an available port starting from start_port"""
    import socket
    
    for port in range(start_port, start_port + max_attempts):
        try:
            # Try to bind to the port
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('localhost', port))
            sock.close()
            return port
        except OSError:
            continue
    return start_port  # Fallback to start_port if none available

def main():
    """Run the web application"""
    print("=" * 60)
    print("Home Automation Web Application")
    print("=" * 60)
    
    # Add current directory to path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    try:
        # Import the app
        from homeauto.web.api import app
        
        # Find available port
        port = find_available_port(8000)
        if port != 8000:
            print(f"\n⚠️  Port 8000 is busy, using port {port} instead")
        
        print(f"\nStarting web server on port {port}...")
        print(f"• Web interface: http://localhost:{port}")
        print(f"• API docs:      http://localhost:{port}/docs")
        print(f"• Alternative:   http://localhost:{port}/redoc")
        print("\nPress Ctrl+C to stop the server")
        print("-" * 60)
        
        # Run the server
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=port,
            reload=False,
            log_level="info"
        )
        
    except ImportError as e:
        print(f"\n❌ Error importing application: {e}")
        print("\nMake sure you have:")
        print("1. Activated the virtual environment")
        print("2. Installed dependencies: pip install -r requirements.txt")
        print("3. Installed the package: pip install -e .")
        return 1
    except KeyboardInterrupt:
        print("\n\nServer stopped by user")
        return 0
    except Exception as e:
        print(f"\n❌ Error running application: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
