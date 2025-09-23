#!/usr/bin/env python3
"""
Build comparison tool for Meetscribe
Compares PyInstaller vs Nuitka builds
"""

import os
import sys
import subprocess
import time
from pathlib import Path
import platform


def run_command_timed(cmd, check=True):
    """Run a command and return execution time and result."""
    start_time = time.time()
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, check=check
        )
        end_time = time.time()
        return end_time - start_time, result
    except subprocess.CalledProcessError as e:
        end_time = time.time()
        return end_time - start_time, e


def get_file_size(file_path):
    """Get file size in MB."""
    try:
        size_bytes = os.path.getsize(file_path)
        return size_bytes / (1024 * 1024)  # Convert to MB
    except OSError:
        return None


def find_executable(dist_dir):
    """Find the executable in the dist directory."""
    dist_path = Path(dist_dir)
    
    if platform.system() == "Darwin":
        # Check for .app bundle first
        app_bundle = dist_path / "meetscribe.app"
        if app_bundle.exists():
            exe_path = app_bundle / "Contents" / "MacOS" / "meetscribe"
            if exe_path.exists():
                return exe_path
        # Check for direct executable
        exe_path = dist_path / "meetscribe"
        if exe_path.exists():
            return exe_path
    elif platform.system() == "Windows":
        exe_path = dist_path / "meetscribe.exe"
        if exe_path.exists():
            return exe_path
    else:
        exe_path = dist_path / "meetscribe"
        if exe_path.exists():
            return exe_path
    
    return None


def test_startup_time(exe_path, iterations=5):
    """Test executable startup time."""
    times = []
    
    for i in range(iterations):
        start_time = time.time()
        try:
            result = subprocess.run(
                [str(exe_path), "--help"],
                capture_output=True,
                text=True,
                timeout=30
            )
            end_time = time.time()
            
            if result.returncode == 0:
                times.append(end_time - start_time)
            else:
                print(f"  ⚠️  Iteration {i+1} failed with return code {result.returncode}")
                
        except subprocess.TimeoutExpired:
            print(f"  ⚠️  Iteration {i+1} timed out")
        except Exception as e:
            print(f"  ⚠️  Iteration {i+1} failed: {e}")
    
    if times:
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        return avg_time, min_time, max_time
    else:
        return None, None, None


def build_and_compare():
    """Build with both systems and compare results."""
    print("🏗️  Meetscribe Build Comparison Tool")
    print("=" * 50)
    
    # Change to project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)
    
    results = {}
    
    # Clean dist directory
    dist_dir = Path("dist")
    if dist_dir.exists():
        import shutil
        shutil.rmtree(dist_dir)
    
    # Test PyInstaller build
    print("\n📦 Testing PyInstaller Build...")
    print("-" * 30)
    
    pyinstaller_time, pyinstaller_result = run_command_timed(
        "python scripts/build_signed.py --no-sign", check=False
    )
    
    if isinstance(pyinstaller_result, subprocess.CalledProcessError):
        print(f"❌ PyInstaller build failed: {pyinstaller_result}")
        results['pyinstaller'] = {'success': False, 'error': str(pyinstaller_result)}
    else:
        print(f"✅ PyInstaller build completed in {pyinstaller_time:.1f}s")
        
        # Find executable
        exe_path = find_executable("dist")
        if exe_path:
            file_size = get_file_size(exe_path)
            avg_startup, min_startup, max_startup = test_startup_time(exe_path)
            
            results['pyinstaller'] = {
                'success': True,
                'build_time': pyinstaller_time,
                'file_size_mb': file_size,
                'avg_startup_time': avg_startup,
                'min_startup_time': min_startup,
                'max_startup_time': max_startup,
                'exe_path': exe_path
            }
            
            print(f"   📁 Executable: {exe_path}")
            print(f"   📏 Size: {file_size:.1f} MB")
            if avg_startup:
                print(f"   ⚡ Startup time: {avg_startup:.2f}s (avg), {min_startup:.2f}s (min), {max_startup:.2f}s (max)")
        else:
            print("❌ PyInstaller executable not found")
            results['pyinstaller'] = {'success': False, 'error': 'Executable not found'}
    
    # Clean for next build
    if dist_dir.exists():
        import shutil
        shutil.rmtree(dist_dir)
    
    # Test Nuitka build
    print("\n⚡ Testing Nuitka Build...")
    print("-" * 30)
    
    nuitka_time, nuitka_result = run_command_timed(
        "python scripts/build_nuitka.py --no-sign", check=False
    )
    
    if isinstance(nuitka_result, subprocess.CalledProcessError):
        print(f"❌ Nuitka build failed: {nuitka_result}")
        results['nuitka'] = {'success': False, 'error': str(nuitka_result)}
    else:
        print(f"✅ Nuitka build completed in {nuitka_time:.1f}s")
        
        # Find executable  
        exe_path = find_executable("dist")
        if exe_path:
            file_size = get_file_size(exe_path)
            avg_startup, min_startup, max_startup = test_startup_time(exe_path)
            
            results['nuitka'] = {
                'success': True,
                'build_time': nuitka_time,
                'file_size_mb': file_size,
                'avg_startup_time': avg_startup,
                'min_startup_time': min_startup,
                'max_startup_time': max_startup,
                'exe_path': exe_path
            }
            
            print(f"   📁 Executable: {exe_path}")
            print(f"   📏 Size: {file_size:.1f} MB")
            if avg_startup:
                print(f"   ⚡ Startup time: {avg_startup:.2f}s (avg), {min_startup:.2f}s (min), {max_startup:.2f}s (max)")
        else:
            print("❌ Nuitka executable not found")
            results['nuitka'] = {'success': False, 'error': 'Executable not found'}
    
    # Display comparison
    print("\n📊 Build Comparison Results")
    print("=" * 50)
    
    if results.get('pyinstaller', {}).get('success') and results.get('nuitka', {}).get('success'):
        pi = results['pyinstaller']
        nu = results['nuitka']
        
        print(f"{'Metric':<20} {'PyInstaller':<15} {'Nuitka':<15} {'Winner'}")
        print("-" * 65)
        
        # Build time
        pi_build = pi['build_time']
        nu_build = nu['build_time']
        build_winner = "PyInstaller" if pi_build < nu_build else "Nuitka"
        print(f"{'Build Time':<20} {pi_build:.1f}s{'':<10} {nu_build:.1f}s{'':<10} {build_winner}")
        
        # File size
        pi_size = pi['file_size_mb']
        nu_size = nu['file_size_mb']
        size_winner = "PyInstaller" if pi_size < nu_size else "Nuitka"
        print(f"{'File Size':<20} {pi_size:.1f} MB{'':<8} {nu_size:.1f} MB{'':<8} {size_winner}")
        
        # Startup time
        if pi['avg_startup_time'] and nu['avg_startup_time']:
            pi_startup = pi['avg_startup_time']
            nu_startup = nu['avg_startup_time']
            startup_winner = "PyInstaller" if pi_startup < nu_startup else "Nuitka"
            print(f"{'Startup Time (avg)':<20} {pi_startup:.2f}s{'':<9} {nu_startup:.2f}s{'':<9} {startup_winner}")
        
        print("\n🏆 Overall Assessment:")
        
        # Calculate scores
        scores = {'pyinstaller': 0, 'nuitka': 0}
        
        if pi_build < nu_build:
            scores['pyinstaller'] += 1
        else:
            scores['nuitka'] += 1
            
        if pi_size < nu_size:
            scores['pyinstaller'] += 1
        else:
            scores['nuitka'] += 1
            
        if pi['avg_startup_time'] and nu['avg_startup_time']:
            if pi['avg_startup_time'] < nu['avg_startup_time']:
                scores['pyinstaller'] += 1
            else:
                scores['nuitka'] += 1
        
        if scores['nuitka'] > scores['pyinstaller']:
            print("✅ Nuitka performs better overall")
        elif scores['pyinstaller'] > scores['nuitka']:
            print("✅ PyInstaller performs better overall")
        else:
            print("🤝 Both systems perform similarly")
            
        print(f"\n🎯 Recommendations:")
        print(f"   • Use Nuitka for: Better performance, smaller size, faster startup")
        print(f"   • Use PyInstaller for: Faster builds, maximum compatibility")
        
    else:
        print("❌ Could not complete full comparison due to build failures")
        
        if not results.get('pyinstaller', {}).get('success'):
            print(f"   PyInstaller: {results.get('pyinstaller', {}).get('error', 'Unknown error')}")
            
        if not results.get('nuitka', {}).get('success'):
            print(f"   Nuitka: {results.get('nuitka', {}).get('error', 'Unknown error')}")


def main():
    """Main function."""
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Build Comparison Tool for Meetscribe")
        print()
        print("This tool builds Meetscribe with both PyInstaller and Nuitka,")
        print("then compares build time, file size, and startup performance.")
        print()
        print("Usage: python scripts/compare_builds.py")
        print()
        print("Note: This will take several minutes as it performs two full builds.")
        return
    
    try:
        build_and_compare()
    except KeyboardInterrupt:
        print("\n🛑 Comparison interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Comparison failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

