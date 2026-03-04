# External Tools Setup

This directory contains third-party tools bundled with Pallet Manager.

## SumatraPDF (Windows only)

### What it does:
- Provides reliable PDF printing on Windows
- Opens print dialog automatically for exported pallets
- Supports batch printing of multiple PDFs

### Setup Instructions:

1. **Download SumatraPDF:**
   - Go to: https://www.sumatrapdfreader.org/download-free-pdf-viewer
   - Download the **portable version** (SumatraPDF-3.5.2-64.zip or latest)
   - Extract the ZIP file

2. **Copy to this directory:**
   ```
   external_tools/
   └── SumatraPDF/
       └── SumatraPDF.exe  (portable executable)
   ```

3. **Verify structure:**
   ```
   external_tools/
   ├── README.md (this file)
   └── SumatraPDF/
       └── SumatraPDF.exe
   ```

4. **Rebuild the app:**
   - The build script will automatically bundle SumatraPDF
   - It will be included in the PyInstaller build
   - Users won't need to install anything separately

### Why SumatraPDF?

- **Lightweight:** Only ~5MB
- **Fast:** Opens instantly
- **Print support:** `-print-dialog` flag opens print dialog directly
- **Batch printing:** Can print multiple PDFs at once
- **Free & Open Source:** MIT license, redistribution allowed
- **No installation needed:** Portable version works perfectly

### Alternative (if SumatraPDF unavailable):

The app will automatically fall back to:
1. Adobe Reader (if installed)
2. Microsoft Edge browser
3. Default PDF viewer with manual print instructions

### License:

SumatraPDF is licensed under AGPL/GPLv3. Redistribution is permitted.
See: https://github.com/sumatrapdfreader/sumatrapdf/blob/master/COPYING







