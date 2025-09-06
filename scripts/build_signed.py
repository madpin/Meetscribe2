#!/usr/bin/env python3
"""
Build script for creating signed macOS applications.
This script handles the complete build and signing process for macOS.
"""

import os
import sys
import subprocess
import shutil


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


def check_codesign_identity():
    """Check if a valid code signing identity is available."""
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


def build_app(sign=True):
    """Build the application using PyInstaller."""
    print("🔨 Building application with PyInstaller...")

    # Clean previous builds
    if os.path.exists("dist"):
        shutil.rmtree("dist")
    if os.path.exists("build"):
        shutil.rmtree("build")

    # Set up environment for signing
    env = os.environ.copy()

    if sign:
        identity = check_codesign_identity()
        if identity:
            env["CODESIGN_IDENTITY"] = identity
            print(f"✅ Code signing enabled with identity: {identity}")
        else:
            print("⚠️  Building without code signing")
            sign = False

    # Ensure we're in the correct directory and spec file exists
    current_dir = os.getcwd()
    spec_file = os.path.join(current_dir, "meetscribe.spec")

    if not os.path.exists(spec_file):
        print(f"❌ ERROR: Spec file not found at: {spec_file}")
        print(f"Current directory: {current_dir}")
        print("Available files:")
        try:
            files = os.listdir(current_dir)
            for file in files:
                print(f"  - {file}")
        except Exception as e:
            print(f"Could not list directory: {e}")
        sys.exit(1)

    print(f"✅ Found spec file: {spec_file}")

    # Run PyInstaller with absolute path
    cmd = f"pyinstaller {spec_file}"
    run_command(cmd, env=env)

    # Additional signing steps for macOS
    if sign and sys.platform == "darwin" and identity:
        app_path = "dist/meetscribe"

        print("🔐 Performing additional code signing...")

        # Sign the executable with hardened runtime
        sign_cmd = (
            f'codesign --force --options runtime --sign "{identity}" '
            f'--entitlements entitlements.plist "{app_path}"'
        )
        run_command(sign_cmd)

        # Verify the signature
        verify_cmd = f'codesign --verify --verbose "{app_path}"'
        run_command(verify_cmd)

        # Check signature details
        check_cmd = f'codesign --display --verbose=2 "{app_path}"'
        run_command(check_cmd)

        print("✅ Application successfully signed!")
        print("\n📝 Next steps for distribution:")
        print("1. Test the signed application")
        print("2. For distribution outside the App Store, " "consider notarization:")
        print(
            "   xcrun notarytool submit dist/meetscribe.zip "
            "--keychain-profile 'AC_PASSWORD'"
        )
        print("3. For internal use, the signed app should work without " "warnings")

    print("\n🎉 Build complete! Executable: dist/meetscribe")
    return True


def main():
    """Main build function."""
    print("🚀 Building Meetscribe for macOS")

    # Change to project root directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    os.chdir(project_root)
    print(f"📁 Changed to project directory: {project_root}")
    print(f"📂 Current working directory: {os.getcwd()}")

    # Verify we're in the correct directory
    if not os.path.exists("meetscribe.spec"):
        print("❌ ERROR: meetscribe.spec not found in current directory!")
        print("This script must be run from the project root or scripts/ subdirectory.")
        print(f"Current directory: {os.getcwd()}")
        print("Available files in current directory:")
        try:
            files = os.listdir(".")
            for file in sorted(files):
                if os.path.isfile(file):
                    print(f"  📄 {file}")
                elif os.path.isdir(file):
                    print(f"  📁 {file}/")
        except Exception as e:
            print(f"Could not list directory: {e}")

        # Try to find meetscribe.spec in common locations
        print("\nSearching for meetscribe.spec in project...")
        for root, dirs, files in os.walk("."):
            if "meetscribe.spec" in files:
                spec_path = os.path.join(root, "meetscribe.spec")
                print(f"Found meetscribe.spec at: {spec_path}")
                break
        else:
            print("meetscribe.spec not found anywhere in project!")

        sys.exit(1)

    # Check if we're on macOS
    if sys.platform != "darwin":
        print("ℹ️  This script is optimized for macOS. " "Building without signing...")
        build_app(sign=False)
        return

    # Check if signing should be attempted
    sign = "--no-sign" not in sys.argv

    if not sign:
        print("🔓 Building without code signing " "(--no-sign flag detected)")

    build_app(sign=sign)


if __name__ == "__main__":
    main()
