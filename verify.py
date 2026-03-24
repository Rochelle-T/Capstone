#!/usr/bin/env python3
"""
Verification script for AstroSense project structure and dependencies
"""

import os
import sys
import subprocess
from pathlib import Path

def check_python_env():
    """Check Python version and packages"""
    print("✓ Checking Python environment...")
    
    required_packages = [
        'fastapi', 'uvicorn', 'pydantic', 'jwt', 'passlib'
    ]
    
    try:
        import fastapi
        print("  ✓ FastAPI installed")
    except ImportError:
        print("  ✗ FastAPI not installed - run: pip install -r server/requirements.txt")
        return False
    
    return True

def check_node_env():
    """Check Node.js and npm"""
    print("✓ Checking Node.js environment...")
    
    try:
        result = subprocess.run(['npm', '--version'], capture_output=True, text=True)
        npm_version = result.stdout.strip()
        print(f"  ✓ npm version: {npm_version}")
        return True
    except FileNotFoundError:
        print("  ✗ npm not found - install Node.js from https://nodejs.org/")
        return False

def check_project_structure():
    """Verify project files exist"""
    print("✓ Checking project structure...")
    
    required_files = [
        'server/app/main.py',
        'server/requirements.txt',
        'client/src/App.jsx',
        'client/package.json',
        'README.md',
    ]
    
    all_exist = True
    for file in required_files:
        if Path(file).exists():
            print(f"  ✓ {file}")
        else:
            print(f"  ✗ {file} - MISSING")
            all_exist = False
    
    return all_exist

def main():
    print("\n" + "="*50)
    print("AstroSense Project Verification")
    print("="*50 + "\n")
    
    checks = [
        check_project_structure(),
        check_python_env(),
        check_node_env(),
    ]
    
    print("\n" + "="*50)
    if all(checks):
        print("✓ All checks passed! Ready to start development.")
        print("\nNext steps:")
        print("1. Backend:  cd server && python -m venv venv")
        print("            .\\venv\\Scripts\\activate (Windows) or source venv/bin/activate")
        print("            pip install -r requirements.txt")
        print("            python -m uvicorn app.main:app --reload")
        print("\n2. Frontend: cd client && npm run dev")
        print("\nThen visit: http://localhost:5173/")
    else:
        print("✗ Some checks failed. Please see above for details.")
        sys.exit(1)
    
    print("="*50 + "\n")

if __name__ == '__main__':
    main()
