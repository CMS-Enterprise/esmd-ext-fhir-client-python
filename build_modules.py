#!/usr/bin/env python3
"""
Build script for EsmdFHIRClient modules.

This script ensures that the shared module is automatically included
when building individual modules.
"""

import os
import sys
import subprocess
from pathlib import Path

def build_shared_module():
    """Build the shared module first."""
    print("🔧 Building shared module...")
    shared_dir = Path("esmd_shared")
    if shared_dir.exists():
        try:
            subprocess.run([
                sys.executable, "setup.py", "install", "--user"
            ], cwd=shared_dir, check=True)
            print("✅ Shared module built successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to build shared module: {e}")
            return False
    else:
        print("⚠️  Shared module directory not found")
        return False
    return True

def build_module(module_name):
    """Build a specific module."""
    print(f"🔧 Building {module_name}...")
    module_dir = Path(module_name)
    if module_dir.exists():
        try:
            subprocess.run([
                sys.executable, "setup.py", "install", "--user"
            ], cwd=module_dir, check=True)
            print(f"✅ {module_name} built successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to build {module_name}: {e}")
            return False
    else:
        print(f"⚠️  {module_name} directory not found")
        return False

def build_all_modules():
    """Build all modules in the correct order."""
    modules = [
        "bundlesubmissionclient",
        "practitionerclient", 
        "documentrefscheduler",
        "notificationscheduler"
    ]
    
    print("🚀 Starting module build process...")
    
    # Build shared module first
    if not build_shared_module():
        print("❌ Shared module build failed. Aborting.")
        return False
    
    # Build individual modules
    success_count = 0
    for module in modules:
        if build_module(module):
            success_count += 1
    
    print(f"\n📊 Build Results: {success_count}/{len(modules)} modules built successfully")
    return success_count == len(modules)

def main():
    """Main build function."""
    if len(sys.argv) > 1:
        # Build specific module
        module_name = sys.argv[1]
        if module_name == "shared":
            success = build_shared_module()
        else:
            # Build shared first, then specific module
            if build_shared_module():
                success = build_module(module_name)
            else:
                success = False
    else:
        # Build all modules
        success = build_all_modules()
    
    if success:
        print("\n🎉 Build completed successfully!")
        print("\n📝 Next steps:")
        print("1. Copy .env.example to .env")
        print("2. Edit .env with your configuration values")
        print("3. Start using the modules!")
    else:
        print("\n⚠️  Build completed with errors. Please check the output above.")
        sys.exit(1)

if __name__ == "__main__":
    main() 