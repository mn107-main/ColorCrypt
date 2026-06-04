# Changelog

All notable changes to this project will be documented in this file.

## [2.2.0] — 2026-06-04

### Added
- **LSB entropy analysis** for steganalysis detection: `_analyze_lsb_entropy()` static method computes per‑channel χ² p‑values; flags images where LSB distribution is too uniform (potential steganography)
- **Separate salt/password input**: `set_settings()` now accepts a `salt` parameter (bytes); `encrypt_data_siv()` passes existing salt through to `generate_key_from_password()`, enabling deterministic key derivation when a user‑supplied salt is provided
- **CLI `--salt` argument**: specify salt as a hex string (requires `--password`); salt is stored in encryption metadata as `SALT:...`
- **GUI salt entry**: new "Соль (hex, optional)" field in the Security tab; persisted in config
- **GUI LSB Entropy Analysis button**: "Анализ LSB‑энтропии" in the Scanner tab — runs χ² test on the loaded image and displays per‑channel statistics (ratio, χ², p‑value) with an overall suspicion verdict (LOW/MEDIUM/HIGH)

### Changed
- `encrypt_data_siv()` passes `self.salt` to `generate_key_from_password()` instead of ignoring it; enables user‑supplied salt override
- `_update_core_settings()` in GUI now parses hex salt from the salt entry field and passes it to the core

### Fixed
- `encrypt_data_siv()` previously always generated a new random salt even if a salt was already set; now respects the pre‑existing salt value

## [2.1.0] — 2026-06-04

### Added
- **K-LSB steganography**: per-channel configurable bit depths (e.g., R=1, G=2, B=3) via `KLSB:R1G2B3` header
- **Adaptive K-LSB**: auto-assigns bit depths based on channel sensitivity (R=1, G=2, B=3, A=1)
- **JPEG output**: lossy format support with forced RGB conversion; data may be corrupted (known limitation)
- **TIFF output**: lossless multi-format image saving
- **ZIP output**: single-file or chunked archive packing with automatic detection/decoding
- **FFmpeg video steganography**: direct `encode_video`/`decode_video` methods in `stego_media.py` using subprocess (frame‑by‑frame PNG pipeline)
- GUI controls for K-LSB channels, adaptive checkbox, ZIP mode, and Video (FFmpeg) codec in Media tab

### Changed
- `OUTPUT_FORMATS` extended: TIFF, JPEG, ZIP (AVIF removed — PIL's lossless mode is not truly lossless)
- `set_settings()` accepts tuple `k_lsb=(1,2,3,1)` and converts to `{'R':1,'G':2,'B':3,'A':1}` internally
- `encode()` wraps single PNG in ZIP when `output_format='ZIP'` and chunk mode is off
- `encode_chunked()` stores basenames in meta JSON for portable ZIP archives
- `decode()` detects `.zip` extension and dispatches to `_decode_zip`
- CLI `--format` now accepts all `OUTPUT_FORMATS` keys
- Language data updated with new UI strings (K-LSB, ZIP mode)

### Fixed
- K-LSB pixel capacity calculation: now correctly accounts for sum of per-channel depths per pixel
- K-LSB bitwise NOT mask on Python int → converted to `np.uint8` to prevent negative overflow
- K-LSB decode offset: aligns to pixel boundary for correct payload extraction
- K-LSB `_decode_lsb_payload_k_lsb` bit interleaving: contiguous per-channel extraction matching encode order
- Chunked ZIP decode remaps file paths to extraction directory
- `encode_chunked` `original_name` parameter made optional (default `None`)

### Removed
- AVIF output format (PIL AVIF encoder is not truly lossless, corrupts pixel data)

## [2.0.0] — 2026-06-04

### Added
- `requirements.txt` with pinned dependencies
- `argon2-cffi` dependency for Argon2 key derivation

### Changed
- **Key derivation**: replaced PBKDF2 (100k iterations) with **Argon2id** (`time_cost=3`, `memory_cost=65536` KiB, `parallelism=4`) — GPU/ASIC-resistant
- **Encryption mode**: replaced AES-256-GCM with **AES-256-SIV** (RFC 5297, PyCryptodome's `MODE_SIV`) — nonce misuse resilient; even if a nonce is reused, only message equality is revealed, not the key or plaintext
- **Salt size**: reduced from 32→16 bytes (sufficient for Argon2)
- UI labels and README updated to reflect new cipher and KDF

### Backward compatible
- Old files encrypted with PBKDF2 + AES-256-GCM are still decryptable via an automatic fallback path (`_decrypt_legacy_gcm`)
- The `mode` field in encryption metadata (`"GCM"` vs `"SIV"`) routes decryption to the correct implementation
