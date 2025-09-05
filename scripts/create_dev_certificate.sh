#!/bin/bash
# Script to create a self-signed certificate for development
# NOTE: This will NOT eliminate security warnings for end users

set -e

echo "🔐 Creating self-signed certificate for development..."
echo "⚠️  WARNING: This certificate will NOT eliminate security warnings for end users"
echo "⚠️  Only an Apple Developer ID certificate ($99/year) can do that"
echo ""

# Check if certificate already exists
if security find-identity -v -p codesigning | grep -q "Terminal App Dev"; then
    echo "✅ Development certificate already exists"
    security find-identity -v -p codesigning | grep "Terminal App Dev"
    exit 0
fi

echo "Creating self-signed certificate..."

# Create the certificate
security create-certificate \
    -c "Terminal App Dev" \
    -t 1 \
    -r \
    -k login.keychain \
    -Z SHA256 \
    -K 2048 \
    -T /usr/bin/codesign

echo ""
echo "✅ Self-signed certificate created: 'Terminal App Dev'"
echo ""
echo "📝 Usage:"
echo "  export CODESIGN_IDENTITY='Terminal App Dev'"
echo "  python scripts/build_signed.py"
echo ""
echo "⚠️  Important Notes:"
echo "- This certificate is only trusted on YOUR Mac"
echo "- Other users will still see security warnings"
echo "- For distribution, you need an Apple Developer ID certificate"
echo "- To get one: https://developer.apple.com/programs/"
