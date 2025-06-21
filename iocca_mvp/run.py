#!/usr/bin/env python3
"""
IOCCA MVP Runner Script
Provides easy ways to run different parts of the system
"""
import argparse
import sys
import os
import subprocess
from config import config

def run_web_server():
    """Run the web server"""
    print("Starting IOCCA MVP Web Server...")
    print(f"Server will be available at: http://{config.app.host}:{config.app.port}")
    
    try:
        import uvicorn
        uvicorn.run(
            "web.app:app", 
            host=config.app.host, 
            port=config.app.port,
            reload=config.app.debug,
            log_level="info"
        )
    except ImportError:
        print("uvicorn not installed. Install with: pip install uvicorn")
        sys.exit(1)

def run_cli_simulation():
    """Run CLI simulation"""
    print("🎯 Running CLI Simulation...")
    from main import simulate_disruption
    simulate_disruption()

def run_tests():
    """Run test suite"""
    print("🧪 Running Test Suite...")
    try:
        result = subprocess.run(["pytest", "-v"], capture_output=False)
        return result.returncode == 0
    except FileNotFoundError:
        print("❌ pytest not installed. Install with: pip install pytest")
        return False

def validate_config():
    """Validate configuration"""
    print("🔧 Validating Configuration...")
    
    if config.validate():
        print("✅ Configuration is valid")
        print(f"📊 OpenAI API Key: {'Set' if config.openai.api_key else 'Not Set'}")
        print(f"🔍 RAG Model: {config.rag.embedding_model}")
        print(f"🎯 Confidence Threshold: {config.rag.confidence_threshold}")
        return True
    else:
        print("❌ Configuration validation failed")
        print("⚠️  Check your environment variables and .env file")
        return False

def install_dependencies():
    """Install project dependencies"""
    print("📦 Installing Dependencies...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        print("Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("Failed to install dependencies")
        return False

def setup_environment():
    """Set up development environment"""
    print("🛠️  Setting up Development Environment...")
    
    # Check if .env exists
    if not os.path.exists(".env"):
        print("📝 Creating .env file from template...")
        if os.path.exists(".env.template"):
            import shutil
            shutil.copy(".env.template", ".env")
            print(".env file created. Please edit it with your configuration.")
        else:
            print(".env.template not found")
            return False
    
    # Install dependencies
    if not install_dependencies():
        return False
    
    # Validate configuration
    if not validate_config():
        print("⚠️  Configuration needs attention, but setup completed")
    
    print("🎉 Development environment setup complete!")
    print("\n📖 Next steps:")
    print("1. Edit .env file with your OpenAI API key")
    print("2. Run 'python run.py web' to start the web server")
    print("3. Run 'python run.py test' to run tests")
    
    return True

def show_help():
    """Show help information"""
    print("""
IOCCA MVP - Intelligent Operations Control Center Assistant

Available commands:

  web         Start the web server interface
  cli         Run CLI simulation
  test        Run the test suite
  config      Validate configuration
  setup       Set up development environment
  install     Install dependencies
  help        Show this help message

Examples:

  python run.py web          # Start web server
  python run.py cli          # Run CLI simulation
  python run.py test         # Run tests
  python run.py config       # Check configuration
  python run.py setup        # Set up environment

For more information, see README.md
""")

def main():
    parser = argparse.ArgumentParser(
        description="IOCCA MVP Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "command",
        choices=["web", "cli", "test", "config", "setup", "install", "help"],
        help="Command to run"
    )
    
    if len(sys.argv) == 1:
        show_help()
        return
    
    args = parser.parse_args()
    
    print("IOCCA MVP - Crew Disruption and Recovery System")
    print("=" * 60)
    
    try:
        if args.command == "web":
            run_web_server()
        elif args.command == "cli":
            run_cli_simulation()
        elif args.command == "test":
            success = run_tests()
            sys.exit(0 if success else 1)
        elif args.command == "config":
            success = validate_config()
            sys.exit(0 if success else 1)
        elif args.command == "setup":
            success = setup_environment()
            sys.exit(0 if success else 1)
        elif args.command == "install":
            success = install_dependencies()
            sys.exit(0 if success else 1)
        elif args.command == "help":
            show_help()
        else:
            show_help()
            
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()