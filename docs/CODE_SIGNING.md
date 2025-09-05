# Code Signing Guide

This guide explains how to set up code signing for your macOS application to eliminate security warnings.

## Overview

When you distribute a macOS application, Apple's Gatekeeper security feature checks if the app is signed with a trusted certificate. Without proper signing, users see the warning:

> "Apple could not verify [app] is free of malware that may harm your Mac"

## Local Development Setup

### Prerequisites

1. **Apple Developer Account** ($99/year)
2. **Xcode Command Line Tools**:
   ```bash
   xcode-select --install
   ```

### Step 1: Create Developer ID Certificate

1. Go to [Apple Developer Portal](https://developer.apple.com/account/resources/certificates)
2. Click "+" to create a new certificate
3. Select "Developer ID Application"
4. Follow the instructions to create and download the certificate
5. Double-click the downloaded `.cer` file to install it in Keychain Access

### Step 2: Verify Certificate Installation

```bash
# Check if certificate is installed
security find-identity -v -p codesigning

# You should see something like:
# 1) ABCD1234... "Developer ID Application: Your Name (TEAMID)"
```

### Step 3: Build Signed Application

```bash
# Activate your virtual environment
source .venv/bin/activate

# Use the automated build script
./scripts/build.sh

# Or use the signing script directly
python scripts/build_signed.py
```

The build script will automatically:
- Detect your code signing certificate
- Sign the application with proper entitlements
- Verify the signature
- Test the executable

## CI/CD Setup (GitHub Actions)

**Code signing is completely optional** - the CI will work fine without certificates and build unsigned executables. Users will just see macOS security warnings.

For automated builds with code signing in GitHub Actions, you need to set up repository secrets.

### Step 1: Export Your Certificate

```bash
# Export certificate as .p12 file (you'll be prompted for a password)
security find-identity -v -p codesigning
# Note the 40-character hash of your "Developer ID Application" certificate

# Export the certificate (replace HASH with your certificate hash)
security export -t cert -f pkcs12 -k login.keychain -P "YOUR_EXPORT_PASSWORD" -o certificate.p12 HASH

# Convert to base64 for GitHub secrets
base64 -i certificate.p12 | pbcopy
```

### Step 2: Configure GitHub Repository Secrets

Go to your repository → Settings → Secrets and variables → Actions

Add these secrets:

| Secret Name | Description | Value |
|-------------|-------------|--------|
| `MACOS_CERTIFICATE` | Base64-encoded .p12 certificate | Output from `base64` command |
| `MACOS_CERTIFICATE_PWD` | Certificate export password | Password you used when exporting |
| `MACOS_CODESIGN_IDENTITY` | Certificate identity hash | 40-character hash from `security find-identity` |

### Step 3: Test CI Build

Push a tag to trigger the release workflow:

```bash
git tag v1.0.0
git push origin v1.0.0
```

The CI will automatically:
- Set up the certificate in the macOS runner
- Build and sign the application
- Create a release with signed executables

## Troubleshooting

### Certificate Issues

**Certificate not found:**
```bash
# List all certificates
security find-identity -v

# Check specific keychain
security find-identity -v -p codesigning login.keychain
```

**Permission denied:**
```bash
# Unlock keychain
security unlock-keychain login.keychain

# Allow codesign to access the key
security set-key-partition-list -S apple-tool:,apple:,codesign: -s -k YOUR_KEYCHAIN_PASSWORD login.keychain
```

### Signature Verification

**Check if app is properly signed:**
```bash
# Verify signature
codesign --verify --verbose dist/aio_terminal_template

# Display signature details
codesign --display --verbose=2 dist/aio_terminal_template

# Check entitlements
codesign --display --entitlements - dist/aio_terminal_template
```

### Common Errors

**"errSecInternalComponent" during signing:**
- Usually means the certificate private key is not accessible
- Try unlocking the keychain: `security unlock-keychain login.keychain`

**"resource fork, Finder information, or similar detritus not allowed":**
- Clean the build directory: `rm -rf build/ dist/`
- Rebuild: `./scripts/build.sh`

**Gatekeeper still shows warnings:**
- Verify the certificate is "Developer ID Application" (not "Mac Developer")
- Check that the certificate hasn't expired
- Ensure you're using the correct certificate hash

## Advanced: Notarization

For even better security (optional), you can notarize your app with Apple:

```bash
# Create a zip file for notarization
ditto -c -k --keepParent dist/aio_terminal_template aio_terminal_template.zip

# Submit for notarization (requires app-specific password)
xcrun notarytool submit aio_terminal_template.zip --keychain-profile "AC_PASSWORD" --wait

# Staple the notarization to your app
xcrun stapler staple dist/aio_terminal_template
```

**Setup for notarization:**
1. Create an app-specific password in your Apple ID account
2. Store it in keychain: `xcrun notarytool store-credentials "AC_PASSWORD" --apple-id "your@email.com" --team-id "TEAMID" --password "APP_SPECIFIC_PASSWORD"`

## Summary

- **For development**: Run `./scripts/build.sh` - it handles everything automatically
- **For CI/CD**: Set up the three GitHub secrets and the workflows will sign releases
- **For distribution**: Signed apps work immediately without security warnings
- **For maximum trust**: Consider notarization for public distribution

## Summary

**Code signing is completely optional** and not required for the application to work:

- ✅ **Without certificates**: CI builds unsigned apps, users see security warnings but can bypass them
- ✅ **With certificates**: CI builds signed apps, no security warnings for users
- ✅ **Local development**: Works with or without certificates
- ✅ **Cross-platform**: Linux and Windows builds work identically regardless

The build scripts are designed to work whether or not you have code signing set up, so you can start developing immediately and add signing later when needed.
