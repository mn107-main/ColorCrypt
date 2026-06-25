# Changelog

## [2.4.0] — 2026-06-25

### Added
- **JPEG DCT steganography** — `stego_jpeg.py` module with JSteg/F5 embedding in DCT coefficients; CLI `jpeg-dct-encode`/`jpeg-dct-decode` modes; GUI checkbox in Settings tab
- **Auto attack mode** — Brute-force extraction of hidden data without password (tries LSB 1-4, K-LSB, DCT); `attack` CLI mode; GUI Attack tab
- **Cloud I/O** — `cloud_io.py` module supporting S3, FTP, and Google Drive upload/download; `cloud-upload`/`cloud-download` CLI modes; GUI Cloud tab
- **Interactive Learning Sandbox** — New GUI tab with step-by-step visualization of LSB steganography (original, stego, difference ×10, LSB layer ×10 contrast, PSNR metrics)
- **All new features** have Russian/English translations in `lang_data.py`

## [2.3.0] — 2026-06-17

### Added
- **ECC level selection** — CLI `--ecc-level 0|1|2|3` and GUI dropdown (0=off, 1=5%, 2=10%, 3=25% redundancy); header format `ECC:{level}`
- **Hex key support** — `--key` CLI arg and hex key entry in GUI Security tab; `key_hex` parameter in `core.set_settings()`
- **RS steganalysis** — Regular/Singular group analysis for detecting LSB steganography; GUI button on Scanner tab
- **Psychovisual K-LSB** — HSV-colorspace-aware bit distribution (more bits to B channel per human perception); `--psychovisual` CLI arg
- **Adaptive per-region LSB depth** — 16×16 block variance analysis selects optimal LSB depth per region; `--adaptive-lsb` CLI arg
- **Streaming mode** — `encode_streaming()` for chunked file processing without full memory load; `--stream` CLI arg; GUI checkbox
- **AAC/OGG audio support** — `encode_aac`/`decode_aac`/`encode_ogg`/`decode_ogg` in `stego_media.py`; codec selection in GUI
- **Image Comparison tab** — GUI tab comparing original vs encoded images (MSE, PSNR, max/avg diff, changed pixel count)
- **Enhanced scan output** — `scan_for_header()` now returns `detected_method` (LSB/K-LSB/III/Direct) and `estimated_data_size`
- **pytest test suite** — 21 tests covering encode/decode, ECC levels & correction, encryption, III, steganalysis (entropy + RS), auto-detect, streaming, psychovisual K-LSB, local adaptive depth, compression, key validation

### Fixed
- K-LSB payload bit padding — payload bits now padded to multiple of `ch_sum` per-channel depth sum
- `auto_detect_params` — now reads raw header bytes first (header is stored raw in LSB mode)
- Adaptive LSB header rebuild — header now contains actual adjusted K-LSB values and payload is re-padded after adaptation
- ECC correction test — now corrupts block byte 0, which XOR parity can correctly locate
- Missing `LSB:`/`KLSB:` header append (regression from refactoring)

### Changed
- Header format: `ECC:1` → `ECC:{ecc_level}` (decode handles both new and old format)
- Language data: 30+ new keys in Russian and English for all new features
- README: updated feature lists, CLI args tables, GUI tabs descriptions

## [2.2.0] — 2026-06

### Added
- Configurable compression levels (none/min/normal/max)
- Salt support for deterministic key derivation (`--salt`)

### Fixed
- (Previous fixes)

## [2.1.0] — 2026-06

### Added
- Image-in-Image (III) steganography with alpha channel preservation
- Media steganography (GIF, MP4, MP3, WAV, Video via FFmpeg)
- Chunk mode for large file support
- ZIP output packing

## [2.0.0] — 2026-06

### Added
- K-LSB per-channel bit depth steganography
- AES-256-SIV encryption with Argon2id KDF
- SHA-256 integrity verification
- LSB entropy analysis (χ² test)
- CLI + Tkinter GUI
- Header scanning across LSB layers and channels

## [1.0.0] — 2026-06

### Added
- Initial release: direct pixel encoding/decoding
- Basic CLI interface
