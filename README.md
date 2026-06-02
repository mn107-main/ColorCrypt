# ColorCrypt

Encode any file into an image (PNG, WebP, BMP, TIFF) and decode it back. Features AES-GCM encryption, zlib compression, integrity verification, **LSB steganography**, chunking for large files, **Image-in-Image steganography** (with alpha preservation), **media steganography (MP4/GIF/MP3)**, and **auto‑header scanning**.

## Features

- **Encode files to images** — embeds file data into pixel channels (mono, RGB, RGBA)
- **LSB steganography** — configurable 1–4 bit LSB embedding for low-noise data hiding
- **Decode images back to original files** — with integrity check (SHA-256)
- **Encryption** — AES-256-GCM with PBKDF2 key derivation (100k iterations)
- **Compression** — zlib compression with configurable levels (none/min/normal/max)
- **Large file support** — automatic chunking (10/50/100/250 MB per image)
- **Image-in-Image** — hide one image inside another using alpha channel (or RGB LSB), with original alpha preservation
- **Media steganography** — embed data into GIF, MP4, or MP3 files (optional: `imageio`, `ffmpeg`, `pydub`)
- **Header scanning** — auto-detect hidden data by scanning LSB layers, channels, and raw bytes
- **Performance** — numpy-vectorized pixel operations, lazy decoding, data caching
- **CLI + GUI** — command-line interface and Tkinter GUI

## Requirements

- Python 3.8+
- `pycryptodome`
- `pillow`
- `numpy`

### Optional dependencies

| Library | Feature |
|---|---|
| `imageio` + `imageio-ffmpeg` | GIF / MP4 steganography |
| `ffmpeg` (system binary) | MP4 / MP3 processing |
| `pydub` | MP3 steganography |
| `tkinterdnd2` | Drag-and-drop in GUI |

Install: `pip install pycryptodome pillow numpy`

Optional: `pip install imageio imageio-ffmpeg pydub`

## CLI Usage

```
# Encode a file to PNG
python core.py encode secret.txt -o output.png

# Encode with password (AES-GCM encryption)
python core.py encode secret.txt -o encrypted.png -p "mypassword"

# Encode with compression and RGB mode
python core.py encode file.bin -o out.png -c normal -m rgb

# Encode with 2-bit LSB steganography (less visible)
python core.py encode secret.txt -o lsb_output.png --lsb-bits 2

# Decode an image back to original file
python core.py decode encoded.png -o restored.txt

# Decode with password
python core.py decode encrypted.png -o restored.txt -p "mypassword"

# Encode large file with chunking
python core.py encode bigfile.iso -o output_folder -c max --chunk --chunk-size 100MB

# Image-in-Image: hide secret.png inside container.png
python core.py iii-encode container.png secret.png -o output.png

# Image-in-Image: extract hidden image (with alpha restoration)
python core.py iii-decode container.png -o extracted.png --restore-container

# Scan image for hidden data (auto-detect)
python core.py scan suspicious.png --scan-layers 4

# Scan with specific channels (RGB only, 2 layers)
python core.py scan image.png --scan-alpha --scan-rgb --scan-layers 2
```

### CLI Arguments


| Argument | Description |
|----------|-------------|
| `mode` | `encode`, `decode`, `iii-encode`, `iii-decode`, `scan` |
| `input` | Input file path |
| `input2` | Second input (secret image for `iii-encode`) |
| `-o, --output` | Output file or directory |
| `-p, --password` | Encryption password |
| `-c, --compress` | Compression level: `none`, `min`, `normal`, `max` (default: `normal`) |
| `-m, --mode` | Color mode: `mono`, `rgb`, `rgba` (default: `rgb`) |
| `--encode-mode` | Always `base64` |
| `--no-integrity` | Disable SHA-256 integrity check |
| `--format` | Image format: `PNG`, `WebP`, `BMP`, `TIFF` (default: `PNG`) |
| `--lsb-bits` | LSB bit depth: `0` (direct), `1..4` (LSB). Default: `0` |
| `--chunk` | Enable chunk mode for large files |
| `--chunk-size` | Chunk size: `10MB`, `50MB`, `100MB`, `250MB` (default: `50MB`) |
| `--no-preserve-name` | Don't store original filename in image header |
| `--no-alpha` | Don't use alpha channel for Image-in-Image |
| `--restore-container` | Restore original alpha channel after III decode |
| `--scan-layers` | Max LSB layers to scan (default: `4`) |
| `--scan-alpha` | Include alpha channel in scan (default: on) |
| `--scan-rgb` | Include RGB channels in scan (default: on) |

## GUI

Run without arguments to launch the Tkinter GUI:

```
python core.py
```

The GUI provides tabs for:
- **Главная** — Encode/Decode files, progress bar, preview
- **Настройки** — Channel mode, LSB bit depth, compression, output format, chunking
- **Безопасность** — AES-256-GCM encryption, password strength meter
- **Пакетная обработка** — Batch encode/decode multiple files
- **Картинка в картинке** — Image-in-Image steganography (hide/reveal with alpha preservation)
- **Медиа (MP4/GIF/MP3)** — Media steganography for video and audio
- **Детектор** — Scan images for hidden ColorCrypt headers (all LSB layers & channels)
- **Отладка** — Debug log viewer

## How it works

1. **File encoding**: Data is base64-encoded, optionally compressed and encrypted, then packed into image pixels. **Direct mode** stores bytes directly in pixel channels; **LSB mode** (`--lsb-bits 1..4`) spreads data across least significant bits for lower visual noise. A header stores metadata: version, original filename, size, SHA-256, compression/encryption flags, and LSB bit depth.
2. **Decoding**: The header is read from the first pixels (always in direct mode for backward compat). If `LSB:N` is found, the payload is extracted using N-bit LSB; otherwise direct mode is used.
3. **Image-in-Image**: A secret image is compressed and its LSB bits are embedded into the alpha channel (or RGB) of a container image. A magic signature (`0xCC0DE5`) enables auto-detection. The original alpha channel LSBs are saved and can be restored (`--restore-container`).
4. **Media steganography**: Data bits are embedded into GIF frame pixels, MP4 YUV (U/V) planes, or MP3 audio samples.
5. **Scanning**: The program searches raw bytes for `V1|...` headers (direct mode) and all LSB layers (1–8 bits) across all channel combinations for the `0xCC0DE5` magic signature (III mode).

## Project structure

```
core.py          — encoding/decoding engine + CLI (performance, Image-in-Image, scanning)
gui.py           — Tkinter graphical interface (all features)
stego_media.py   — optional media steganography (GIF, MP4, MP3)
```
