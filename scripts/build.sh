#!/bin/bash
# Build script for AIO Terminal Template with optional code signing

set -e  # Exit on any error

echo "🚀 Building AIO Terminal Template..."

# Check if we're on macOS
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "🍎 Detected macOS - checking for code signing capabilities..."
    
    # Check for code signing identity
    if security find-identity -v -p codesigning | grep -q "Developer ID Application"; then
        echo "✅ Code signing identity found - building signed app"
        python scripts/build_signed.py
    else
        echo "⚠️  No code signing identity found"
        echo "Building unsigned app (will show security warning when run)"
        echo ""
        echo "To enable code signing:"
        echo "1. Join the Apple Developer Program"
        echo "2. Create a Developer ID Application certificate"
        echo "3. Install it in your Keychain"
        echo ""
        python scripts/build_signed.py --no-sign
    fi
else
    echo "🐧 Building for non-macOS platform"
    pyinstaller aio_terminal_template.spec
fi

echo ""
echo "🎉 Build complete!"
echo "📁 Executable location: dist/aio_terminal_template"

# Test the executable
if [[ -f "dist/aio_terminal_template" ]]; then
    echo "🧪 Testing executable..."
    ./dist/aio_terminal_template --help
    echo "✅ Executable works!"
else
    echo "❌ Build failed - executable not found"
    exit 1
fi
