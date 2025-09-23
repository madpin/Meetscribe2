#!/usr/bin/env python3
"""
Nuitka build script for creating optimized single-file executables.
This script handles the complete build and signing process using Nuitka.
"""

import os
import sys
import subprocess
import shutil
import platform
from pathlib import Path


def run_command(cmd, check=True, capture_output=False, env=None):
    """Run a shell command and handle errors."""
    print(f"Running: {cmd}")
    if capture_output:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, env=env
        )
        if check and result.returncode != 0:
            print(f"Command failed: {cmd}")
            print(f"stdout: {result.stdout}")
            print(f"stderr: {result.stderr}")
            sys.exit(1)
        return result
    else:
        result = subprocess.run(cmd, shell=True, env=env)
        if check and result.returncode != 0:
            print(f"Command failed: {cmd}")
            sys.exit(1)
        return result


def check_nuitka_installed():
    """Check if Nuitka is installed."""
    try:
        result = run_command("/opt/homebrew/bin/python3.11 -m nuitka --version", check=False, capture_output=True)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"✅ Nuitka is installed: {version}")
            return True
        else:
            print("❌ Nuitka is not installed or not accessible")
            return False
    except Exception as e:
        print(f"❌ Error checking Nuitka installation: {e}")
        return False


def install_nuitka():
    """Install Nuitka if not already installed."""
    print("📦 Installing Nuitka...")
    run_command("/opt/homebrew/bin/python3.11 -m pip install nuitka")
    print("✅ Nuitka installed successfully")


def check_codesign_identity():
    """Check if a valid code signing identity is available (macOS only)."""
    if platform.system() != "Darwin":
        return None
        
    result = run_command(
        "security find-identity -v -p codesigning", check=False, capture_output=True
    )

    if result.returncode != 0 or "0 valid identities found" in result.stdout:
        print("⚠️  No valid code signing identity found.")
        print("To sign your app, you need:")
        print("1. An Apple Developer account")
        print("2. A valid Developer ID Application certificate")
        print("3. The certificate installed in your Keychain")
        print("\nFor now, building unsigned executable...")
        return None

    # Extract the first valid identity
    lines = result.stdout.split("\n")
    for line in lines:
        if "Developer ID Application:" in line:
            # Extract the identity hash (40 character hex string)
            parts = line.strip().split()
            if len(parts) >= 2:
                identity = parts[1]
                print(f"✅ Found code signing identity: {identity}")
                return identity

    print("⚠️  No Developer ID Application certificate found.")
    return None


def get_nuitka_options(project_root, sign=False, identity=None):
    """Get Nuitka build options based on the project configuration."""
    
    options = [
        # Core compilation options
        "--onefile",  # Create single file executable
        "--assume-yes-for-downloads",  # Auto-download dependencies
        
        # Performance options  
        "--python-flag=no_docstrings",  # Remove docstrings to save space
        "--python-flag=no_annotations",  # Remove annotations to save space
        
        # Console application - enable console (this is a CLI tool)
        "--enable-console",
        
        # Output options
        "--output-filename=meetscribe",
        f"--output-dir={project_root}/dist",
        
        # Include data files
        f"--include-data-file={project_root}/config.toml=config.toml",
        
        # Module inclusion/exclusion options based on PyInstaller spec
        "--nofollow-import-to=pytest",
        "--nofollow-import-to=matplotlib",
        "--nofollow-import-to=scipy",
        "--nofollow-import-to=pandas",
        "--nofollow-import-to=sklearn",
        "--nofollow-import-to=scikit-learn",
        "--nofollow-import-to=numba",
        "--nofollow-import-to=IPython",
        "--nofollow-import-to=jupyter",
        "--nofollow-import-to=notebook",
        "--nofollow-import-to=tkinter",
        "--nofollow-import-to=PyQt5",
        "--nofollow-import-to=PyQt6",
        "--nofollow-import-to=PySide2",
        "--nofollow-import-to=PySide6",
        "--nofollow-import-to=wx",
        
        # Force inclusion of modules that are commonly missed by static analysis
        # Only include modules that are known to cause issues
        "--include-package=deepgram",
        "--include-package=httpx",
    ]
    
    # Platform-specific options
    if platform.system() == "Darwin":  # macOS
        options.extend([
            "--macos-create-app-bundle",  # Create .app bundle
            "--macos-app-icon=none",  # Suppress icon warning
        ])
        
        # Code signing options for macOS
        if sign and identity:
            options.extend([
                f"--macos-sign-identity={identity}",
                f"--macos-sign-tool=codesign",
                "--macos-signed-app-name=Meetscribe",
            ])
    
    elif platform.system() == "Windows":
        # No Windows-specific options needed for console apps
        pass
    
    return options


def build_with_nuitka(project_root, sign=True):
    """Build the application using Nuitka."""
    print("🔨 Building application with Nuitka...")
    
    # Check if Nuitka is installed
    if not check_nuitka_installed():
        install_nuitka()
        if not check_nuitka_installed():
            print("❌ Failed to install or verify Nuitka")
            sys.exit(1)
    
    # Clean previous builds
    dist_dir = Path(project_root) / "dist"
    build_dir = Path(project_root) / "build"
    
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    if build_dir.exists():
        shutil.rmtree(build_dir)
    
    dist_dir.mkdir(exist_ok=True)
    
    # Check for code signing identity on macOS
    identity = None
    if platform.system() == "Darwin" and sign:
        identity = check_codesign_identity()
        if not identity:
            sign = False
    
    # Get Nuitka options
    options = get_nuitka_options(project_root, sign, identity)
    
    # Build the command - use Python 3.11 explicitly to match where Nuitka is installed
    entry_point = Path(project_root) / "app" / "cli.py"
    cmd_parts = ["/opt/homebrew/bin/python3.11", "-m", "nuitka"] + options + [str(entry_point)]
    cmd = " ".join(cmd_parts)
    
    print(f"🚀 Starting Nuitka compilation...")
    print(f"📍 Entry point: {entry_point}")
    print(f"📁 Output directory: {dist_dir}")
    
    # Run Nuitka compilation
    try:
        run_command(cmd)
    except Exception as e:
        print(f"❌ Nuitka compilation failed: {e}")
        sys.exit(1)
    
    # Verify the executable was created
    if platform.system() == "Darwin":
        exe_path = dist_dir / "meetscribe.app" / "Contents" / "MacOS" / "meetscribe"
        if not exe_path.exists():
            # Try alternative path
            exe_path = dist_dir / "meetscribe"
    else:
        exe_path = dist_dir / "meetscribe"
        if platform.system() == "Windows":
            exe_path = dist_dir / "meetscribe.exe"
    
    if not exe_path.exists():
        print(f"❌ Build failed - executable not found at {exe_path}")
        print("Available files in dist directory:")
        if dist_dir.exists():
            for item in dist_dir.rglob("*"):
                if item.is_file():
                    print(f"  📄 {item}")
        sys.exit(1)
    
    print(f"✅ Build successful! Executable: {exe_path}")
    
    # Additional signing for macOS if not done during compilation
    if platform.system() == "Darwin" and sign and identity:
        perform_additional_signing(exe_path, identity, project_root)
    
    return exe_path


def perform_additional_signing(exe_path, identity, project_root):
    """Perform additional code signing steps for macOS."""
    print("🔐 Performing additional code signing...")
    
    entitlements_file = Path(project_root) / "entitlements.plist"
    
    if entitlements_file.exists():
        # Sign with entitlements
        sign_cmd = (
            f'codesign --force --options runtime --sign "{identity}" '
            f'--entitlements "{entitlements_file}" "{exe_path}"'
        )
    else:
        # Sign without entitlements
        sign_cmd = (
            f'codesign --force --options runtime --sign "{identity}" "{exe_path}"'
        )
    
    run_command(sign_cmd)
    
    # Verify the signature
    verify_cmd = f'codesign --verify --verbose "{exe_path}"'
    run_command(verify_cmd)
    
    # Check signature details
    check_cmd = f'codesign --display --verbose=2 "{exe_path}"'
    run_command(check_cmd)
    
    print("✅ Additional signing completed!")


def test_executable(exe_path):
    """Test the built executable."""
    print("🧪 Testing executable...")
    
    try:
        # Test with --help flag
        test_cmd = f'"{exe_path}" --help'
        result = run_command(test_cmd, check=False, capture_output=True)
        
        if result.returncode == 0:
            print("✅ Executable works!")
            return True
        else:
            print(f"❌ Executable test failed with return code {result.returncode}")
            print(f"stdout: {result.stdout}")
            print(f"stderr: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error testing executable: {e}")
        return False


def main():
    """Main build function."""
    print("🚀 Building Meetscribe with Nuitka")
    print(f"🖥️  Platform: {platform.system()} {platform.machine()}")
    print(f"🐍 Python: {sys.version}")
    
    # Change to project root directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)
    
    print(f"📁 Project directory: {project_root}")
    print(f"📂 Current working directory: {os.getcwd()}")
    
    # Verify we're in the correct directory
    if not (project_root / "app" / "cli.py").exists():
        print("❌ ERROR: app/cli.py not found in project root!")
        print("This script must be run from the project root or scripts/ subdirectory.")
        sys.exit(1)
    
    # Check if signing should be attempted
    sign = "--no-sign" not in sys.argv
    
    if not sign:
        print("🔓 Building without code signing (--no-sign flag detected)")
    
    # Build the application
    exe_path = build_with_nuitka(project_root, sign=sign)
    
    # Test the executable
    if test_executable(exe_path):
        print("\n🎉 Build complete and tested successfully!")
        print(f"📁 Executable location: {exe_path}")
        
        if platform.system() == "Darwin" and sign:
            print("\n📝 Next steps for distribution:")
            print("1. Test the signed application on different machines")
            print("2. For distribution outside the App Store, consider notarization:")
            print("   xcrun notarytool submit <your-app>.zip --keychain-profile 'AC_PASSWORD'")
            print("3. For internal use, the signed app should work without warnings")
    else:
        print("❌ Build completed but executable test failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
