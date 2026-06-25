# ColorCrypt

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**ColorCrypt** — это инструмент для сокрытия любых файлов внутри изображений (PNG, WebP, BMP, TIFF, JPEG) с возможностью восстановления оригинала. Проект сочетает современные методы криптографии (AES-256-SIV + Argon2id), сжатия (zlib) и LSB-стеганографии (включая адаптивный K-LSB с разной глубиной на канал), поддерживает работу с большими файлами через автоматическую сегментацию (в т.ч. упаковку в ZIP), а также предоставляет расширенные возможности: встраивание изображения в изображение (Image-in-Image) и медиа-стеганографию (GIF, MP4, MP3, WAV, FLAC, Video через FFmpeg). Наличие CLI и Tkinter GUI делает инструмент доступным как для автоматизации, так и для повседневного использования.

## Возможности

*   **Кодирование файлов в изображения** — встраивание данных в пиксельные каналы (монохромный, RGB, RGBA).
*   **LSB-стеганография** — настраиваемое LSB-встраивание (1–4 бита) для минимизации визуальных искажений, **а также K-LSB** (разная глубина на канал: R, G, B, A) с адаптивным авто-режимом.
*   **LSB-энтропия (стеганоанализ)** — χ²-тест на равномерность распределения LSB-битов для выявления подозрительных изображений (потенциальная стеганография).
*   **RS-стеганоанализ (Regular/Singular)** — более точный метод обнаружения LSB-стеганографии на основе анализа регулярных и сингулярных групп.
*   **Восстановление файлов из изображений** — с проверкой целостности через SHA-256.
*   **Шифрование** — AES-256-SIV (стойкость к повтору nonce) с Argon2id (GPU-устойчивый KDF, 64 MB памяти).
*   **Сжатие** — zlib с настраиваемыми уровнями (none/min/normal/max).
*   **Поддержка больших файлов** — автоматическая сегментация (10/50/100/250 МБ на изображение) с возможностью упаковки в ZIP.
*   **Форматы вывода** — PNG, WebP, BMP, TIFF (lossless), JPEG (lossy), ZIP (упаковка результатов).
*   **Изображение в изображении (III)** — сокрытие одного изображения внутри другого с использованием альфа-канала (или RGB LSB) и сохранением оригинального альфа-канала.
*   **ECC (коррекция ошибок)** — XOR-паритетная коррекция ошибок с настраиваемым уровнем (5%/10%/25%) для повышения устойчивости к сжатию JPEG и шумам канала.
*   **Авто-детекция параметров** — автоматическое определение LSB/K-LSB параметров при декодировании.
*   **Шумовая адаптация K-LSB** — анализ дисперсии каналов для оптимального распределения битов глубины.
*   **Медиа-стеганография** — встраивание данных в файлы GIF, MP4, MP3, WAV, FLAC, AAC, OGG или видео через FFmpeg (опционально: imageio, ffmpeg, pydub).
*   **Настраиваемый уровень ECC** — выбор уровня коррекции ошибок: 5%, 10% или 25% избыточности.
*   **Улучшенное сканирование** — детектор показывает не только наличие данных, но и предполагаемый метод (LSB/K-LSB/III) и размер данных.
*   **Автоматическое сканирование заголовков** — обнаружение скрытых данных перебором LSB-слоёв, каналов и сырых байтов.
*   **Психовизиальная модель K-LSB** — распределение битов по каналам на основе HSV-цветового пространства (глаз менее чувствителен к изменениям в синем/жёлтом каналах).
*   **Адаптивная LSB-глубина по области** — автоматический выбор глубины LSB для каждой области изображения на основе локальной дисперсии (3 бита в текстурах, 1 на гладких участках).
*   **Сравнение изображений** — в GUI добавлена вкладка для сравнения оригинала и изображения со встроенными данными (MSE/PSNR, визуализация разницы, предпросмотр diff-изображения).
*   **Поддержка ключей в hex** — возможность использовать готовый ключ (в hex-формате) вместо пароля.
*   **Потоковый режим** — обработка файлов произвольного размера без полной загрузки в память.
*   **Производительность** — векторизованные операции с пикселями (numpy), ленивое декодирование, кэширование данных.
*   **CLI + GUI** — интерфейс командной строки и графический интерфейс на Tkinter.

## Требования

*   Python 3.8+
*   `pycryptodome`
*   `pillow`
*   `numpy`
*   `argon2-cffi`

### Опциональные зависимости

| Библиотека | Функциональность |
|---|---|
| `imageio` + `imageio-ffmpeg` | Стеганография для GIF / MP4 |
| `ffmpeg` (системный бинарный файл) | Обработка MP4 / MP3 / Video стеганография |
| `pydub` | Стеганография для MP3 |
| `tkinterdnd2` | Drag-and-drop в GUI |

## Установка

```bash
# Основные зависимости
pip install -r requirements.txt

# Опциональные зависимости
pip install imageio imageio-ffmpeg pydub
```

## Использование CLI

### Базовое кодирование/декодирование

```bash
# Кодирование файла в PNG
python core.py encode secret.txt -o output.png

# Кодирование с паролем (AES-256-SIV + Argon2id шифрование)
python core.py encode secret.txt -o encrypted.png -p "mypassword"

# Кодирование со сжатием и RGB-режимом
python core.py encode file.bin -o out.png -c normal -m rgb

# Кодирование с 2-битным LSB (менее заметно)
python core.py encode secret.txt -o lsb_output.png --lsb-bits 2

# Кодирование с ECC-коррекцией ошибок (для JPEG)
python core.py encode secret.txt -o jpeg_output.png --format JPEG --ecc

# Декодирование изображения обратно в файл
python core.py decode encoded.png -o restored.txt

# Декодирование с паролем
python core.py decode encrypted.png -o restored.txt -p "mypassword"
```

### Большие файлы (сегментация)

```bash
python core.py encode bigfile.iso -o output_folder -c max --chunk --chunk-size 100MB
```

### Изображение в изображении (III)

```bash
# Сокрытие secret.png внутри container.png
python core.py iii-encode container.png secret.png -o output.png

# Извлечение скрытого изображения (с восстановлением альфа-канала)
python core.py iii-decode container.png -o extracted.png --restore-container
```

### Сканирование

```bash
# Сканирование изображения на наличие скрытых данных (автоопределение)
python core.py scan suspicious.png --scan-layers 4

# Сканирование только RGB-каналов (2 слоя)
python core.py scan image.png --scan-alpha --scan-rgb --scan-layers 2
```

### Аргументы CLI

| Аргумент | Описание |
|---|---|
| `mode` | `encode`, `decode`, `iii-encode`, `iii-decode`, `scan` |
| `input` | Путь к входному файлу |
| `input2` | Второй входной файл (секретное изображение для `iii-encode`) |
| `-o, --output` | Выходной файл или директория |
| `-p, --password` | Пароль для шифрования |
| `-c, --compress` | Уровень сжатия: `none`, `min`, `normal`, `max` (по умолчанию: `normal`) |
| `-m, --mode` | Цветовой режим: `mono`, `rgb`, `rgba` (по умолчанию: `rgb`) |
| `--encode-mode` | Всегда `base64` |
| `--no-integrity` | Отключить проверку целостности SHA-256 |
| `--format` | Формат изображения: `PNG`, `WebP`, `BMP`, `TIFF`, `JPEG`, `ZIP` (по умолчанию: `PNG`) |
| `--lsb-bits` | Глубина LSB: `0` (прямой), `1..4` (LSB). По умолчанию: `0` |
| `--chunk` | Включить режим сегментации для больших файлов |
| `--chunk-size` | Размер сегмента: `10MB`, `50MB`, `100MB`, `250MB` (по умолчанию: `50MB`) |
| `--no-preserve-name` | Не сохранять исходное имя файла в заголовке изображения |
| `--no-alpha` | Не использовать альфа-канал для Image-in-Image |
| `--restore-container` | Восстановить оригинальный альфа-канал после III декодирования |
| `--scan-layers` | Максимальное количество LSB-слоёв для сканирования (по умолчанию: `4`) |
| `--scan-alpha` | Включить альфа-канал в сканирование (по умолчанию: вкл) |
| `--scan-rgb` | Включить RGB-каналы в сканирование (по умолчанию: вкл) |
| `--ecc` | Включить коррекцию ошибок (ECC) для JPEG |
| `--ecc-level` | Уровень ECC: `0` (выкл), `1` (5%), `2` (10%), `3` (25%) |
| `--key` | Ключ шифрования в hex (альтернатива `--password`) |
| `--psychovisual` | Психовизиальная модель K-LSB (HSV) |
| `--adaptive-lsb` | Адаптивный K-LSB (автовыбор глубины по области) |
| `--stream` | Потоковый режим (без полной загрузки в память) |

### Новое в v2.4.0

- **Визуализация разницы в Сравнении изображений** — diff-изображение отображается как превью (Canvas), кнопка «Сохранить как» для экспорта
- **Прогресс-бар в Сканере** — индикатор выполнения для операций сканирования, энтропии и RS-анализа
- **Кнопка «Сохранить как» в Сканере** — экспорт результатов в текстовый файл
- **Drag-and-drop** для полей Original/Encoded на вкладке сравнения

## GUI

Запустите без аргументов для открытия графического интерфейса Tkinter:

```bash
python core.py
```

GUI предоставляет вкладки для:

*   **Главная** — Кодирование/декодирование файлов, прогресс-бар, предпросмотр
*   **Настройки** — Режим каналов, глубина LSB / K-LSB, сжатие, формат вывода, сегментация, ZIP-упаковка, уровень ECC, психовизиальная модель
*   **Безопасность** — AES-256-SIV шифрование (стойкость к повтору nonce) + Argon2id, индикатор сложности пароля, поддержка ключей в hex
*   **Пакетная обработка** — Пакетное кодирование/декодирование нескольких файлов
*   **Картинка в картинке** — III-стеганография (сокрытие/извлечение с сохранением альфа-канала)
*   **Медиа (GIF/MP4/MP3/WAV/FLAC/AAC/OGG/Video)** — Медиа-стеганография для видео и аудио
*   **Детектор** — Сканирование изображений на наличие скрытых заголовков ColorCrypt (все LSB-слои и каналы), χ²-анализ LSB-энтропии и RS-стеганоанализ для выявления стеганографии
*   **Сравнение изображений** — Визуализация разницы (MSE/PSNR) между оригиналом и изображением со встроенными данными
*   **Отладка** — Просмотр логов отладки

## Как это работает

1.  **Кодирование файла:** Данные проходят Base64-кодирование, опционально сжимаются и шифруются, после чего упаковываются в пиксели изображения. В **прямом режиме** байты записываются напрямую в каналы пикселей; в **LSB-режиме** (`--lsb-bits 1..4`) данные распределяются по младшим битам для снижения визуального шума. В **K-LSB-режиме** каждый канал использует свою глубину (например, R=1, G=2, B=3), записанную в заголовке как `KLSB:R1G2B3`. Заголовок хранит метаданные: версию, исходное имя файла, размер, SHA-256, флаги сжатия/шифрования и глубину LSB.
2.  **Декодирование:** Заголовок считывается из первых пикселей (всегда в прямом режиме для обратной совместимости). Если обнаружена метка `LSB:N`, полезная нагрузка извлекается с использованием N-битного LSB; в противном случае используется прямой режим.
3.  **Изображение в изображении (III):** Секретное изображение сжимается, и его LSB-биты встраиваются в альфа-канал (или RGB) контейнерного изображения. Магическая сигнатура (`0xCC0DE5`) обеспечивает автоматическое обнаружение. Оригинальные LSB альфа-канала сохраняются и могут быть восстановлены (`--restore-container`).
4.  **Медиа-стеганография:** Биты данных встраиваются в пиксели кадров GIF, YUV-плоскости (U/V) видео, аудиосэмплы MP3 или покадрово через FFmpeg.
5.  **Сканирование:** Программа ищет в сырых байтах заголовки `V1|...` (прямой режим), а также во всех LSB-слоях (1–8 бит) и комбинациях каналов — магическую сигнатуру `0xCC0DE5` (режим III).

## Структура проекта

*   `core.py` — движок кодирования/декодирования + CLI (производительность, Image-in-Image, сканирование)
*   `gui.py` — графический интерфейс Tkinter (все функции)
*   `stego_media.py` — опциональная медиа-стеганография (GIF, MP4, MP3, Video FFmpeg)

---

# ColorCrypt (English)

**ColorCrypt** is a tool for encoding any file into an image (PNG, WebP, BMP, TIFF, JPEG) and decoding it back. It combines modern cryptography (AES-256-SIV + Argon2id), compression (zlib), and LSB steganography (including adaptive K-LSB with per-channel bit depth), supports large files via automatic chunking (with optional ZIP packing), and offers extended features like Image‑in‑Image steganography and media steganography (MP4, GIF, MP3, Video via FFmpeg). Both CLI and Tkinter GUI are available.

## Features

- **Encode files to images** — embeds file data into pixel channels (mono, RGB, RGBA)
- **LSB steganography** — configurable 1–4 bit LSB embedding for low‑noise data hiding, plus **K-LSB** (per-channel depth: R, G, B, A) with adaptive auto‑mode
- **LSB entropy (steganalysis)** — χ² test on LSB bit distribution to flag images with suspiciously uniform LSBs (potential steganography)
- **RS steganalysis (Regular/Singular)** — advanced method for detecting LSB steganography via regular/singular group analysis
- **Decode images back to original files** — with SHA‑256 integrity check
- **Encryption** — AES‑256‑SIV (nonce misuse resistant) with Argon2id (GPU‑resistant KDF, 64 MB memory)
- **Compression** — zlib with configurable levels (none/min/normal/max)
- **Large file support** — automatic chunking (10/50/100/250 MB per image) with optional ZIP packing
- **Output formats** — PNG, WebP, BMP, TIFF (lossless), JPEG (lossy), ZIP (archive bundling)
- **Image‑in‑Image** — hide one image inside another using alpha channel (or RGB LSB), with original alpha preservation
- **Media steganography** — embed data into GIF, MP4, MP3, WAV, FLAC, AAC, OGG, or Video via FFmpeg (optional: imageio, ffmpeg, pydub)
- **Header scanning** — auto‑detect hidden data by scanning LSB layers, channels, and raw bytes
- **Enhanced scan output** — shows detected method (LSB/K-LSB/III) and estimated data size
- **RS steganalysis (Regular/Singular)** — advanced LSB detection via regular/singular group analysis
- **Psychovisual K-LSB model** — perceputally-tuned bit distribution using HSV color space
- **Adaptive per-region LSB depth** — selects LSB depth per region based on local variance
- **Image comparison in GUI** — side-by-side diff, MSE/PSNR metrics, visual diff preview thumbnail, Save Diff button
- **Hex key support** — use raw hex key instead of password for encryption
- **Streaming mode** — process arbitrarily large files without full memory load
- **Configurable ECC level** — choose 5%, 10%, or 25% XOR parity redundancy
- **ECC (error correction)** — XOR parity error correction with configurable level for JPEG resilience
- **Performance** — numpy‑vectorized pixel operations, lazy decoding, data caching
- **CLI + GUI** — command‑line interface and Tkinter GUI

## Requirements

- Python 3.8+
- `pycryptodome`
- `pillow`
- `numpy`
- `argon2-cffi`

### Optional dependencies

| Library | Feature |
|---|---|
| `imageio` + `imageio-ffmpeg` | GIF / MP4 steganography |
| `ffmpeg` (system binary) | MP4 / MP3 / Video steganography |
| `pydub` | MP3 steganography |
| `tkinterdnd2` | Drag‑and‑drop in GUI |

## Installation

```bash
# Core dependencies
pip install -r requirements.txt

# Optional dependencies
pip install imageio imageio-ffmpeg pydub
```

## CLI Usage

### Basic encode/decode

```bash
# Encode a file to PNG
python core.py encode secret.txt -o output.png

# Encode with password (AES-256-SIV + Argon2id encryption)
python core.py encode secret.txt -o encrypted.png -p "mypassword"

# Encode with compression and RGB mode
python core.py encode file.bin -o out.png -c normal -m rgb

# Encode with 2-bit LSB (less visible)
python core.py encode secret.txt -o lsb_output.png --lsb-bits 2

# Decode image back to original file
python core.py decode encoded.png -o restored.txt

# Decode with password
python core.py decode encrypted.png -o restored.txt -p "mypassword"
```

### Large files (chunking)

```bash
python core.py encode bigfile.iso -o output_folder -c max --chunk --chunk-size 100MB
```

### Image‑in‑Image

```bash
# Hide secret.png inside container.png
python core.py iii-encode container.png secret.png -o output.png

# Extract hidden image (with alpha restoration)
python core.py iii-decode container.png -o extracted.png --restore-container
```

### Encryption with custom salt

```bash
# Encode with explicit salt (hex string) for deterministic key derivation
python core.py encode secret.txt -o encrypted.png -p "mypassword" --salt a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6

# Decode (salt is automatically read from image metadata)
python core.py decode encrypted.png -o restored.txt -p "mypassword"
```

### LSB Entropy Analysis (Steganalysis)

LSB entropy analysis is available through the GUI (Scanner tab → "Анализ LSB‑энтропии" button in RU / "LSB Entropy Analysis" button in EN) and programmatically via `core.analyze_lsb_entropy()`. It uses a χ² test on per‑channel LSB distribution to flag images with suspiciously uniform LSBs — a common indicator of steganographic embedding.

### Scanning

```bash
# Scan image for hidden data (auto-detect)
python core.py scan suspicious.png --scan-layers 4

# Scan RGB only (2 layers)
python core.py scan image.png --scan-alpha --scan-rgb --scan-layers 2
```

### CLI Arguments

| Argument | Description |
|---|---|
| `mode` | `encode`, `decode`, `iii-encode`, `iii-decode`, `scan` |
| `input` | Input file path |
| `input2` | Second input (secret image for `iii-encode`) |
| `-o, --output` | Output file or directory |
| `-p, --password` | Encryption password |
| `--salt` | Salt in hex (requires `--password`; random if omitted) |
| `-c, --compress` | Compression level: `none`, `min`, `normal`, `max` (default: `normal`) |
| `-m, --mode` | Color mode: `mono`, `rgb`, `rgba` (default: `rgb`) |
| `--encode-mode` | Always `base64` |
| `--no-integrity` | Disable SHA-256 integrity check |
| `--format` | Image format: `PNG`, `WebP`, `BMP`, `TIFF`, `JPEG`, `ZIP` (default: `PNG`) |
| `--lsb-bits` | LSB bit depth: `0` (direct), `1..4` (LSB). Default: `0` |
| `--chunk` | Enable chunk mode for large files |
| `--chunk-size` | Chunk size: `10MB`, `50MB`, `100MB`, `250MB` (default: `50MB`) |
| `--no-preserve-name` | Don't store original filename in image header |
| `--no-alpha` | Don't use alpha channel for Image‑in‑Image |
| `--restore-container` | Restore original alpha channel after III decode |
| `--scan-layers` | Max LSB layers to scan (default: `4`) |
| `--scan-alpha` | Include alpha channel in scan (default: on) |
| `--scan-rgb` | Include RGB channels in scan (default: on) |
| `--ecc` | Enable error correction (ECC) for JPEG |
| `--ecc-level` | ECC level: `0` (off), `1` (5%), `2` (10%), `3` (25%) |
| `--key` | Encryption key in hex (alternative to `--password`) |
| `--psychovisual` | Psychovisual K-LSB model (HSV) |
| `--adaptive-lsb` | Adaptive K-LSB (auto depth per region) |
| `--stream` | Streaming mode (no full memory load) |

### New in v2.4.0

- **Diff preview in Image Comparison** — diff image shown as thumbnail (Canvas), "Save as" button to export
- **Progress bar in Scanner** — indeterminate indicator for scan, entropy, and RS operations
- **"Save as" in Scanner** — export results to a text file
- **Drag-and-drop** for Original/Encoded fields on the Compare tab

## GUI

Run without arguments to launch the Tkinter GUI:

```bash
python core.py
```

The GUI provides tabs for:

- **Home** — Encode/Decode files, progress bar, preview
- **Settings** — Channel mode, LSB / K-LSB bit depth, compression, output format, chunking, ZIP packing, ECC level, psychovisual model
- **Security** — AES‑256‑SIV (nonce misuse resistant) + Argon2id, password strength meter, hex key support
- **Batch** — Batch encode/decode multiple files
- **Image‑in‑Image** — III steganography (hide/reveal with alpha preservation)
- **Media (GIF/MP4/MP3/WAV/FLAC/AAC/OGG/Video)** — Media steganography for video and audio
- **Detector** — Scan images for hidden ColorCrypt headers (all LSB layers & channels), χ² LSB entropy analysis, and RS steganalysis to detect steganography
- **Image Comparison** — Visualize difference (MSE/PSNR) between original and encoded images
- **Debug** — Debug log viewer

## How it works

1. **File encoding:** Data is Base64‑encoded, optionally compressed and encrypted, then packed into image pixels. **Direct mode** stores bytes directly in pixel channels; **LSB mode** (`--lsb-bits 1..4`) spreads data across least significant bits for lower visual noise. **K-LSB mode** uses per-channel bit depths (e.g., R=1, G=2, B=3) stored as `KLSB:R1G2B3` in the header. A header stores metadata: version, original filename, size, SHA‑256, compression/encryption flags, and LSB bit depth.
2. **Decoding:** The header is read from the first pixels (always in direct mode for backward compatibility). If `LSB:N` is found, the payload is extracted using N‑bit LSB; otherwise direct mode is used.
3. **Image‑in‑Image:** A secret image is compressed and its LSB bits are embedded into the alpha channel (or RGB) of a container image. A magic signature (`0xCC0DE5`) enables auto‑detection. The original alpha channel LSBs are saved and can be restored (`--restore-container`).
4. **Media steganography:** Data bits are embedded into GIF frame pixels, video YUV (U/V) planes via FFmpeg, or MP3 audio samples.
5. **Scanning:** The program searches raw bytes for `V1|...` headers (direct mode) and all LSB layers (1–8 bits) across all channel combinations for the `0xCC0DE5` magic signature (III mode).

## Future Ideas

- **JPEG Resilience** — embed data in DCT coefficients (JSteg/F5) instead of LSB to survive JPEG recompression
- **Auto-Attack / Detection** — reverse function that brute-forces parameters (bit depth, mode) to extract hidden messages without a password
- **Cloud Extension** — direct upload/download of encoded images via S3, FTP, or Google Drive
- **Interactive Learning Mode** — sandbox tab in GUI showing bit-level changes during embedding step-by-step

## Project structure

- `core.py` — encoding/decoding engine + CLI (performance, Image‑in‑Image, scanning)
- `gui.py` — Tkinter graphical interface (all features)
- `stego_media.py` — optional media steganography (GIF, MP4, MP3, Video FFmpeg)