#!/bin/bash
# Script to fix macOS security issues with downloaded executables
# This removes the quarantine attribute that causes security warnings

set -e

if [[ $# -eq 0 ]]; then
    echo "Usage: $0 <executable-file>"
    echo ""
    echo "Example:"
    echo "  ./scripts/fix_macos_security.sh dist/meetscribe"
    echo "  ./scripts/fix_macos_security.sh ~/Downloads/meetscribe-macos"
    echo ""
    echo "This script removes the macOS quarantine attribute that causes security warnings."
    exit 1
fi

EXECUTABLE="$1"

if [[ ! -f "$EXECUTABLE" ]]; then
    echo "❌ File not found: $EXECUTABLE"
    exit 1
fi

echo "🔧 Removing quarantine attribute from: $EXECUTABLE"

# Remove quarantine attribute
xattr -d com.apple.quarantine "$EXECUTABLE" 2>/dev/null || echo "ℹ️  No quarantine attribute found (this is normal)"

# Make executable if not already
chmod +x "$EXECUTABLE"

echo "✅ Security fix applied!"
echo ""
echo "You can now run the executable:"
echo "  $EXECUTABLE --help"
echo ""
echo "Note: The first time you run it, you may still see a dialog asking for permission."
echo "Click 'Open' to allow it to run."
