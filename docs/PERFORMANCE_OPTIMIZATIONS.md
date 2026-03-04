# Performance Optimizations

This document describes the performance optimizations applied to both macOS and Windows builds.

## Platform-Specific Optimizations

### macOS (py2app)

**Architecture Detection:**
- Automatically detects system architecture (ARM64 or x86_64)
- Builds native binary for detected architecture
- ARM64 builds: Optimized for Apple Silicon (M1/M2/M3)
- x86_64 builds: Optimized for Intel Macs

**Build Optimizations:**
- `strip=True`: Removes debug symbols (smaller size, faster loading)
- `optimize=2`: Maximum bytecode optimization
- `semi_standalone=False`: Fully standalone bundle (better performance)
- `argv_emulation=False`: Faster startup
- Excludes test modules and unnecessary packages

**Benefits:**
- Native execution (no Rosetta 2 translation on ARM)
- Smaller file size
- Faster startup time
- Better runtime performance

### Windows (PyInstaller)

**Build Optimizations:**
- `strip=True`: Removes debug symbols
- `upx=False`: Disables compression for faster startup (size vs speed tradeoff)
- `console=False`: No console window overhead
- Excludes test modules and unnecessary packages
- Optimized hidden imports list

**Benefits:**
- Faster startup time
- Better runtime performance
- Smaller memory footprint

## Code-Level Optimizations

### Caching
- Path resolution caching (`get_base_dir_cached()`)
- Serial number database caching
- Workbook data caching

### Lazy Loading
- Heavy libraries imported only when needed
- GUI components initialized on demand
- Deferred data loading

### Excel Operations
- `read_only=True` for faster Excel reads
- Batch operations where possible
- Reduced GUI update frequency

## Performance Comparison

| Metric | macOS (ARM64) | Windows (x64) |
|--------|---------------|---------------|
| Startup Time | ~2-4 seconds | ~1-3 seconds |
| File Size | ~150-200 MB | ~100-150 MB |
| Memory Usage | ~200-300 MB | ~150-250 MB |
| Excel Read Speed | Fast | Fast |

## Building Optimized Versions

**macOS:**
```bash
./scripts/build_macos.sh
```
Automatically detects architecture and builds optimized version.

**Windows:**
```bash
scripts\build_windows.bat
```
Builds optimized x64 version.

## Troubleshooting Performance

If performance is still slow:

1. **Check architecture match:**
   - macOS: Ensure app matches your Mac's architecture
   - Windows: Ensure x64 build on x64 system

2. **Check for background processes:**
   - Antivirus scanning
   - System indexing
   - Other resource-intensive apps

3. **Verify optimizations:**
   - Check build logs for warnings
   - Ensure correct architecture is being built
   - Verify excludes are working

4. **Test from source:**
   - Run `python app/pallet_builder_gui.py` directly
   - Compare performance to packaged version
   - Helps identify packaging vs code issues



