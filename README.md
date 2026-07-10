# Hex Viewer

Windows desktop hex viewer built with Python and tkinter.

## Features

- Open binary files and Intel HEX files.
- Display data as offset, hex bytes, and ASCII.
- Configure bytes per row with positive integers only.
- Use the horizontal scrollbar for very wide rows.
- Search byte-boundary hex patterns with `?` nibble wildcards.
- Type odd nibble counts such as `49F`; it is searched as `49 F?`.
- Jump to offsets with decimal by default, or switch the offset base to hexadecimal.

## Run

```powershell
python app.py
```

## Build Release

```powershell
powershell -ExecutionPolicy Bypass -File .\build_release.ps1
```

The release executable is generated at `dist\HexViewer.exe`.
