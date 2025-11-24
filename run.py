"""Production runner script"""
import os
import sys
import subprocess
from pathlib import Path

def check_dependencies():
    """Check if required services are available"""
    try:
        import redis
        import psycopg2
        print("✓ Dependencies installed")
    except ImportError as e:
        print(f"✗ Missing dependency: {e}")
        sys.exit(1)

def setup_database():
    """Initialize database tables"""
    try:
        from models import create_tables
        create_tables()
        print("✓ Database tables created")
    except Exception as e:
        print(f"✗ Database setup failed: {e}")
        sys.exit(1)

def main():
    """Main runner"""
    print("🥬 Food Spoilage Detection System")
    print("=" * 40)
    
    # Check environment
    env_file = Path(".env")
    if not env_file.exists():
        print("⚠️  .env file not found. Copy .env.example to .env and configure.")
        return
    
    # Check dependencies
    check_dependencies()
    
    # Setup database
    setup_database()
    
    # Start application
    print("\n🚀 Starting Streamlit application...")
    print("📊 Dashboard will be available at: http://localhost:8501")
    print("🔄 Press Ctrl+C to stop")
    
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "app.py",
            "--server.port=8501",
            "--server.address=0.0.0.0"
        ])
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")

if __name__ == "__main__":
    main()