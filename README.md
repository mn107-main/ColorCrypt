# ColorCrypt

Encode any file into an image (PNG, WebP, BMP) and decode it back. Features AES-GCM encryption, zlib compression, integrity verification, and chunking for large files.

## Features

- **Encode files to images** — embeds file data into pixel channels (mono, RGB, RGBA)
- **Decode images back to original files** — with integrity check (SHA-256)
- **Encryption** — AES-256-GCM with PBKDF2 key derivation
- **Compression** — zlib compression with configurable levels (none/min/normal/max)
- **Large file support** — automatic chunking (10/50/100/250 MB per image)
- **CLI + GUI** — command-line interface and Tkinter GUI

## Requirements

- Python 3.8+
- `pycryptodome`
- `pillow`

Install: `pip install pycryptodome pillow`

## CLI Usage

```
# Encode a file to PNG
python core.py encode secret.txt -o output.png

# Encode with password (AES-GCM encryption)
python core.py encode secret.txt -o encrypted.png -p "mypassword"

# Encode with compression and RGB mode
python core.py encode file.bin -o out.png -c normal -m rgb

# Decode an image back to original file
python core.py decode encoded.png -o restored.txt

# Decode with password
python core.py decode encrypted.png -o restored.txt -p "mypassword"

# Encode large file with chunking
python core.py encode bigfile.iso -o output_folder -c max --chunk --chunk-size 100MB
```

### CLI Arguments

| Argument | Description |
|---|---|
| `mode` | `encode` or `decode` |
| `input` | Input file path |
| `-o, --output` | Output file or directory |
| `-p, --password` | Encryption password |
| `-c, --compress` | Compression level: `none`, `min`, `normal`, `max` (default: `normal`) |
| `-m, --mode` | Color mode: `mono`, `rgb`, `rgba` (default: `rgb`) |
| `--encode-mode` | Always `base64` |
| `--no-integrity` | Disable SHA-256 integrity check |
| `--format` | Image format: `PNG`, `WebP`, `BMP` (default: `PNG`) |
| `--chunk` | Enable chunk mode for large files |
| `--chunk-size` | Chunk size: `10MB`, `50MB`, `100MB`, `250MB` (default: `50MB`) |
| `--no-preserve-name` | Don't store original filename in image header |

## GUI

Run without arguments to launch the Tkinter GUI:

```
python core.py
```

The GUI provides tabs for Encode, Decode, Settings, and Batch processing.

## How it works

1. File data is base64-encoded, optionally compressed and encrypted
2. Data is packed into image pixels (each channel byte stores one data byte)
3. A header stores metadata: original filename, size, SHA-256, compression flag, encryption flag, encode mode
4. During decoding, the header is read, data is extracted and reversed (decrypt → decompress → base64-decode)

## Project structure

```
core.py   — encoding/decoding engine + CLI
gui.py    — Tkinter graphical interface
```
