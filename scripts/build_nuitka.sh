#!/bin/bash
# Nuitka build script for Meetscribe
# Alternative to PyInstaller build using Nuitka for better performance

set -e  # Exit on any error

echo "🚀 Building Meetscribe with Nuitka..."

# Check if we're on macOS
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "🍎 Detected macOS - checking for code signing capabilities..."
    
    # Check for code signing identity
    if security find-identity -v -p codesigning | grep -q "Developer ID Application"; then
        echo "✅ Code signing identity found - building signed app"
        python scripts/build_nuitka.py
    else
        echo "⚠️  No code signing identity found"
        echo "Building unsigned app (will show security warning when run)"
        echo ""
        echo "To enable code signing:"
        echo "1. Join the Apple Developer Program"
        echo "2. Create a Developer ID Application certificate"
        echo "3. Install it in your Keychain"
        echo ""
        python scripts/build_nuitka.py --no-sign
    fi
else
    echo "🐧 Building for non-macOS platform"
    python scripts/build_nuitka.py --no-sign
fi

echo ""
echo "🎉 Build complete!"

# Find the executable (handle different platforms)
if [[ "$OSTYPE" == "darwin"* ]]; then
    # Check for .app bundle first
    if [[ -d "dist/meetscribe.app" ]]; then
        echo "📁 Executable location: dist/meetscribe.app"
        echo "🧪 Testing executable..."
        ./dist/meetscribe.app/Contents/MacOS/meetscribe --help
    elif [[ -f "dist/meetscribe" ]]; then
        echo "📁 Executable location: dist/meetscribe"
        echo "🧪 Testing executable..."
        ./dist/meetscribe --help
    else
        echo "❌ Build failed - executable not found"
        exit 1
    fi
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    # Windows
    if [[ -f "dist/meetscribe.exe" ]]; then
        echo "📁 Executable location: dist/meetscribe.exe"
        echo "🧪 Testing executable..."
        ./dist/meetscribe.exe --help
    else
        echo "❌ Build failed - executable not found"
        exit 1
    fi
else
    # Linux and others
    if [[ -f "dist/meetscribe" ]]; then
        echo "📁 Executable location: dist/meetscribe"
        echo "🧪 Testing executable..."
        ./dist/meetscribe --help
    else
        echo "❌ Build failed - executable not found"
        exit 1
    fi
fi

echo "✅ Executable works!"

echo ""
echo "🔍 Build comparison:"
echo "  🏗️  Nuitka: Compiled Python with C++ performance"
echo "  📦 PyInstaller: Bundled Python interpreter"
echo "  ⚡ Nuitka typically starts faster and uses less memory"
echo "  🎯 Nuitka produces truly optimized machine code"

