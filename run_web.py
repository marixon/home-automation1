#!/usr/bin/env python3
"""
Simple script to run the Home Automation web application
"""

import sys
import os
import uvicorn

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
        
        print("\nStarting web server...")
        print("• Web interface: http://localhost:8000")
        print("• API docs:      http://localhost:8000/docs")
        print("• Alternative:   http://localhost:8000/redoc")
        print("\nPress Ctrl+C to stop the server")
        print("-" * 60)
        
        # Run the server
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            reload=False,  # Set to True for development
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
