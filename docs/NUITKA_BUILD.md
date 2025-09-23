# Nuitka Build System for Meetscribe

This document describes the alternative Nuitka-based build system for Meetscribe, which provides an alternative to the PyInstaller build system with potentially better performance and smaller executable sizes.

## Overview

Nuitka is a Python compiler that translates Python code to C++ and then compiles it to machine code. This approach typically results in:

- **Faster startup times** - No Python interpreter to load
- **Better runtime performance** - Optimized machine code instead of interpreted bytecode
- **Smaller memory footprint** - No need to load the entire Python runtime
- **Better dependency analysis** - More precise inclusion/exclusion of modules

## Quick Start

### Prerequisites

1. **Python 3.10+** - Same as the main project
2. **C++ Compiler** - Platform specific:
   - **macOS**: Xcode Command Line Tools (`xcode-select --install`)
   - **Windows**: Microsoft Visual Studio Build Tools or Visual Studio Community
   - **Linux**: GCC/G++ (`sudo apt install build-essential` on Ubuntu)

### Building

#### Simple Build (Recommended)
```bash
# Use the automated build script
./scripts/build_nuitka.sh
```

#### Advanced Build
```bash
# Run the Python build script directly
python scripts/build_nuitka.py

# Build without code signing (macOS)
python scripts/build_nuitka.py --no-sign
```

### Installation of Dependencies

If you haven't already installed the development dependencies:

```bash
# Install all development dependencies including Nuitka
pip install -e ".[dev]"

# Or install just Nuitka
pip install nuitka
```

## Build Configuration

The build configuration is stored in `nuitka.config.toml`. You can modify this file to customize the build process:

### Key Configuration Options

```toml
[build]
onefile = true                    # Create single executable file
disable_console = false          # Set true for GUI apps
python_flag_no_docstrings = true # Remove docstrings for smaller size
enable_anti_bloat_plugin = true  # Remove unused code automatically

# Data files to bundle
data_files = [
    { source = "config.toml", dest = "config.toml" }
]

# Force include specific modules
include_modules = [
    "ssl", "_ssl", "cryptography", "deepgram"
]

# Exclude heavy/unused modules  
exclude_modules = [
    "pytest", "matplotlib", "scipy", "pandas"
]
```

### Platform-Specific Options

```toml
[macos]
create_app_bundle = true    # Create .app bundle on macOS
signed_app_name = "Meetscribe"

[windows]  
console_mode = "disable"    # Hide console window on Windows
```

## Build Process Details

### What the Build Script Does

1. **Dependency Check**: Verifies Nuitka is installed
2. **Clean Build**: Removes previous build artifacts
3. **Code Analysis**: Nuitka analyzes the entire codebase
4. **C++ Generation**: Converts Python code to optimized C++
5. **Compilation**: Compiles C++ to native machine code
6. **Bundling**: Creates single executable with all dependencies
7. **Code Signing**: Signs the executable (macOS with valid certificates)
8. **Testing**: Runs basic functionality test

### Output Locations

- **macOS**: `dist/meetscribe.app` (app bundle) or `dist/meetscribe`
- **Windows**: `dist/meetscribe.exe`
- **Linux**: `dist/meetscribe`

## Code Signing (macOS)

The build system automatically handles code signing if you have a valid Developer ID certificate:

### Automatic Signing
```bash
# Will auto-detect and sign if certificate is available
./scripts/build_nuitka.sh
```

### Manual Signing Control
```bash
# Force unsigned build
./scripts/build_nuitka.sh --no-sign
python scripts/build_nuitka.py --no-sign
```

### Setting Up Code Signing

1. **Join Apple Developer Program** ($99/year)
2. **Create Developer ID Certificate** in Apple Developer portal
3. **Download and install** the certificate in Keychain Access
4. **Verify installation**:
   ```bash
   security find-identity -v -p codesigning
   ```

## Performance Comparison

| Aspect | PyInstaller | Nuitka |
|--------|-------------|--------|
| **Startup Time** | ~2-3 seconds | ~0.5-1 second |
| **Memory Usage** | Higher (full Python runtime) | Lower (optimized code only) |
| **File Size** | Larger (includes interpreter) | Smaller (compiled code) |
| **Build Time** | Fast (~1-2 min) | Slower (~5-10 min) |
| **Compatibility** | Very high | High (some edge cases) |
| **Performance** | Python speed | Near-C speed |

## Troubleshooting

### Common Issues

#### 1. Missing C++ Compiler
**Error**: `error: Microsoft Visual C++ 14.0 is required`

**Solution**:
- **Windows**: Install Visual Studio Build Tools
- **macOS**: Run `xcode-select --install` 
- **Linux**: Install build tools (`sudo apt install build-essential`)

#### 2. Module Not Found at Runtime
**Error**: `ModuleNotFoundError: No module named 'xyz'`

**Solution**: Add the module to `include_modules` in `nuitka.config.toml`:
```toml
include_modules = [
    "xyz",  # Add your missing module here
    # ... other modules
]
```

#### 3. Large Executable Size
**Problem**: Executable is too large

**Solutions**:
- Enable more exclusions in `nuitka.config.toml`
- Use `--python-flag=no_docstrings` and `--python-flag=no_annotations`
- Review and exclude unnecessary dependencies

#### 4. Slow Build Times
**Problem**: Build takes too long

**Solutions**:
- Use `--assume-yes-for-downloads` (already enabled)
- Build on SSD storage
- Use `--jobs=N` where N is number of CPU cores
- Consider using binary cache (Nuitka commercial)

#### 5. Runtime Errors with Dynamic Imports
**Problem**: Code using `importlib` or `__import__` fails

**Solution**: Use `--include-module=` for dynamically imported modules

### Advanced Debugging

#### Enable Verbose Output
```bash
python scripts/build_nuitka.py --debug
```

#### Check Dependencies
```bash
# List all imported modules
python -c "import pkg_resources; print([d.project_name for d in pkg_resources.working_set])"
```

#### Test Specific Modules
```bash
# Test if a module can be imported
python -c "import your_problematic_module; print('OK')"
```

## Integration with CI/CD

### GitHub Actions Example
```yaml
- name: Build with Nuitka
  run: |
    pip install -e ".[dev]"
    ./scripts/build_nuitka.sh --no-sign
    
- name: Upload Artifact
  uses: actions/upload-artifact@v3
  with:
    name: meetscribe-nuitka
    path: dist/
```

### Docker Build Example
```dockerfile
FROM python:3.11-slim

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and build
COPY . /app
WORKDIR /app
RUN pip install -e ".[dev]"
RUN python scripts/build_nuitka.py --no-sign
```

## Migrating from PyInstaller

If you're switching from the PyInstaller build:

1. **Dependencies**: Nuitka is already added to `pyproject.toml`
2. **Build Command**: Use `./scripts/build_nuitka.sh` instead of `./scripts/build.sh`
3. **Configuration**: Modify `nuitka.config.toml` instead of `meetscribe.spec`
4. **Testing**: Both systems create similar outputs in `dist/`

## Support and Resources

- **Nuitka Documentation**: https://nuitka.net/doc/
- **Nuitka GitHub**: https://github.com/Nuitka/Nuitka
- **Performance Tips**: https://nuitka.net/pages/overview.html
- **Commercial Support**: https://nuitka.net/doc/commercial.html

## Contributing

When contributing build system improvements:

1. Test on multiple platforms
2. Update this documentation
3. Verify both signed and unsigned builds work
4. Test with fresh Python environments
5. Consider backwards compatibility

