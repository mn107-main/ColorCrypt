# ColorCrypt

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**ColorCrypt** — это инструмент для сокрытия любых файлов внутри изображений (PNG, WebP, BMP, TIFF) с возможностью восстановления оригинала. Проект сочетает современные методы криптографии (AES-256-GCM), сжатия (zlib) и LSB-стеганографии, поддерживает работу с большими файлами через автоматическую сегментацию, а также предоставляет расширенные возможности: встраивание изображения в изображение (Image-in-Image) и медиа‑стеганографию (MP4, GIF, MP3). Наличие CLI и Tkinter GUI делает инструмент доступным как для автоматизации, так и для повседневного использования.

## Возможности

*   **Кодирование файлов в изображения** — встраивание данных в пиксельные каналы (монохромный, RGB, RGBA).
*   **LSB-стеганография** — настраиваемое LSB-встраивание (1–4 бита) для минимизации визуальных искажений.
*   **Восстановление файлов из изображений** — с проверкой целостности через SHA-256.
*   **Шифрование** — AES-256-GCM с PBKDF2 (100 000 итераций).
*   **Сжатие** — zlib с настраиваемыми уровнями (none/min/normal/max).
*   **Поддержка больших файлов** — автоматическая сегментация (10/50/100/250 МБ на изображение).
*   **Изображение в изображении (III)** — сокрытие одного изображения внутри другого с использованием альфа-канала (или RGB LSB) и сохранением оригинального альфа-канала.
*   **Медиа-стеганография** — встраивание данных в файлы GIF, MP4 или MP3 (опционально: imageio, ffmpeg, pydub).
*   **Автоматическое сканирование заголовков** — обнаружение скрытых данных перебором LSB-слоёв, каналов и сырых байтов.
*   **Производительность** — векторизованные операции с пикселями (numpy), ленивое декодирование, кэширование данных.
*   **CLI + GUI** — интерфейс командной строки и графический интерфейс на Tkinter.

## Требования

*   Python 3.8+
*   `pycryptodome`
*   `pillow`
*   `numpy`

### Опциональные зависимости

| Библиотека | Функциональность |
|---|---|
| `imageio` + `imageio-ffmpeg` | Стеганография для GIF / MP4 |
| `ffmpeg` (системный бинарный файл) | Обработка MP4 / MP3 |
| `pydub` | Стеганография для MP3 |
| `tkinterdnd2` | Drag-and-drop в GUI |

## Установка

```bash
# Основные зависимости
pip install pycryptodome pillow numpy

# Опциональные зависимости
pip install imageio imageio-ffmpeg pydub
```

## Использование CLI

### Базовое кодирование/декодирование

```bash
# Кодирование файла в PNG
python core.py encode secret.txt -o output.png

# Кодирование с паролем (AES-GCM шифрование)
python core.py encode secret.txt -o encrypted.png -p "mypassword"

# Кодирование со сжатием и RGB-режимом
python core.py encode file.bin -o out.png -c normal -m rgb

# Кодирование с 2-битным LSB (менее заметно)
python core.py encode secret.txt -o lsb_output.png --lsb-bits 2

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
| `--format` | Формат изображения: `PNG`, `WebP`, `BMP`, `TIFF` (по умолчанию: `PNG`) |
| `--lsb-bits` | Глубина LSB: `0` (прямой), `1..4` (LSB). По умолчанию: `0` |
| `--chunk` | Включить режим сегментации для больших файлов |
| `--chunk-size` | Размер сегмента: `10MB`, `50MB`, `100MB`, `250MB` (по умолчанию: `50MB`) |
| `--no-preserve-name` | Не сохранять исходное имя файла в заголовке изображения |
| `--no-alpha` | Не использовать альфа-канал для Image-in-Image |
| `--restore-container` | Восстановить оригинальный альфа-канал после III декодирования |
| `--scan-layers` | Максимальное количество LSB-слоёв для сканирования (по умолчанию: `4`) |
| `--scan-alpha` | Включить альфа-канал в сканирование (по умолчанию: вкл) |
| `--scan-rgb` | Включить RGB-каналы в сканирование (по умолчанию: вкл) |

## GUI

Запустите без аргументов для открытия графического интерфейса Tkinter:

```bash
python core.py
```

GUI предоставляет вкладки для:

*   **Главная** — Кодирование/декодирование файлов, прогресс-бар, предпросмотр
*   **Настройки** — Режим каналов, глубина LSB, сжатие, формат вывода, сегментация
*   **Безопасность** — AES-256-GCM шифрование, индикатор сложности пароля
*   **Пакетная обработка** — Пакетное кодирование/декодирование нескольких файлов
*   **Картинка в картинке** — III-стеганография (сокрытие/извлечение с сохранением альфа-канала)
*   **Медиа (MP4/GIF/MP3)** — Медиа-стеганография для видео и аудио
*   **Детектор** — Сканирование изображений на наличие скрытых заголовков ColorCrypt (все LSB-слои и каналы)
*   **Отладка** — Просмотр логов отладки

## Как это работает

1.  **Кодирование файла:** Данные проходят Base64-кодирование, опционально сжимаются и шифруются, после чего упаковываются в пиксели изображения. В **прямом режиме** байты записываются напрямую в каналы пикселей; в **LSB-режиме** (`--lsb-bits 1..4`) данные распределяются по младшим битам для снижения визуального шума. Заголовок хранит метаданные: версию, исходное имя файла, размер, SHA-256, флаги сжатия/шифрования и глубину LSB.
2.  **Декодирование:** Заголовок считывается из первых пикселей (всегда в прямом режиме для обратной совместимости). Если обнаружена метка `LSB:N`, полезная нагрузка извлекается с использованием N-битного LSB; в противном случае используется прямой режим.
3.  **Изображение в изображении (III):** Секретное изображение сжимается, и его LSB-биты встраиваются в альфа-канал (или RGB) контейнерного изображения. Магическая сигнатура (`0xCC0DE5`) обеспечивает автоматическое обнаружение. Оригинальные LSB альфа-канала сохраняются и могут быть восстановлены (`--restore-container`).
4.  **Медиа-стеганография:** Биты данных встраиваются в пиксели кадров GIF, YUV-плоскости (U/V) MP4 или аудиосэмплы MP3.
5.  **Сканирование:** Программа ищет в сырых байтах заголовки `V1|...` (прямой режим), а также во всех LSB-слоях (1–8 бит) и комбинациях каналов — магическую сигнатуру `0xCC0DE5` (режим III).

## Структура проекта

*   `core.py` — движок кодирования/декодирования + CLI (производительность, Image-in-Image, сканирование)
*   `gui.py` — графический интерфейс Tkinter (все функции)
*   `stego_media.py` — опциональная медиа-стеганография (GIF, MP4, MP3)

---

# ColorCrypt (English)

**ColorCrypt** is a tool for encoding any file into an image (PNG, WebP, BMP, TIFF) and decoding it back. It combines modern cryptography (AES-256-GCM), compression (zlib), and LSB steganography, supports large files via automatic chunking, and offers extended features like Image‑in‑Image steganography and media steganography (MP4, GIF, MP3). Both CLI and Tkinter GUI are available.

## Features

- **Encode files to images** — embeds file data into pixel channels (mono, RGB, RGBA)
- **LSB steganography** — configurable 1–4 bit LSB embedding for low‑noise data hiding
- **Decode images back to original files** — with SHA‑256 integrity check
- **Encryption** — AES‑256‑GCM with PBKDF2 key derivation (100k iterations)
- **Compression** — zlib with configurable levels (none/min/normal/max)
- **Large file support** — automatic chunking (10/50/100/250 MB per image)
- **Image‑in‑Image** — hide one image inside another using alpha channel (or RGB LSB), with original alpha preservation
- **Media steganography** — embed data into GIF, MP4, or MP3 files (optional: imageio, ffmpeg, pydub)
- **Header scanning** — auto‑detect hidden data by scanning LSB layers, channels, and raw bytes
- **Performance** — numpy‑vectorized pixel operations, lazy decoding, data caching
- **CLI + GUI** — command‑line interface and Tkinter GUI

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
| `tkinterdnd2` | Drag‑and‑drop in GUI |

## Installation

```bash
# Core dependencies
pip install pycryptodome pillow numpy

# Optional dependencies
pip install imageio imageio-ffmpeg pydub
```

## CLI Usage

### Basic encode/decode

```bash
# Encode a file to PNG
python core.py encode secret.txt -o output.png

# Encode with password (AES-GCM encryption)
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
| `-c, --compress` | Compression level: `none`, `min`, `normal`, `max` (default: `normal`) |
| `-m, --mode` | Color mode: `mono`, `rgb`, `rgba` (default: `rgb`) |
| `--encode-mode` | Always `base64` |
| `--no-integrity` | Disable SHA-256 integrity check |
| `--format` | Image format: `PNG`, `WebP`, `BMP`, `TIFF` (default: `PNG`) |
| `--lsb-bits` | LSB bit depth: `0` (direct), `1..4` (LSB). Default: `0` |
| `--chunk` | Enable chunk mode for large files |
| `--chunk-size` | Chunk size: `10MB`, `50MB`, `100MB`, `250MB` (default: `50MB`) |
| `--no-preserve-name` | Don't store original filename in image header |
| `--no-alpha` | Don't use alpha channel for Image‑in‑Image |
| `--restore-container` | Restore original alpha channel after III decode |
| `--scan-layers` | Max LSB layers to scan (default: `4`) |
| `--scan-alpha` | Include alpha channel in scan (default: on) |
| `--scan-rgb` | Include RGB channels in scan (default: on) |

## GUI

Run without arguments to launch the Tkinter GUI:

```bash
python core.py
```

The GUI provides tabs for:

- **Home** — Encode/Decode files, progress bar, preview
- **Settings** — Channel mode, LSB bit depth, compression, output format, chunking
- **Security** — AES‑256‑GCM encryption, password strength meter
- **Batch** — Batch encode/decode multiple files
- **Image‑in‑Image** — III steganography (hide/reveal with alpha preservation)
- **Media (MP4/GIF/MP3)** — Media steganography for video and audio
- **Detector** — Scan images for hidden ColorCrypt headers (all LSB layers & channels)
- **Debug** — Debug log viewer

## How it works

1. **File encoding:** Data is Base64‑encoded, optionally compressed and encrypted, then packed into image pixels. **Direct mode** stores bytes directly in pixel channels; **LSB mode** (`--lsb-bits 1..4`) spreads data across least significant bits for lower visual noise. A header stores metadata: version, original filename, size, SHA‑256, compression/encryption flags, and LSB bit depth.
2. **Decoding:** The header is read from the first pixels (always in direct mode for backward compatibility). If `LSB:N` is found, the payload is extracted using N‑bit LSB; otherwise direct mode is used.
3. **Image‑in‑Image:** A secret image is compressed and its LSB bits are embedded into the alpha channel (or RGB) of a container image. A magic signature (`0xCC0DE5`) enables auto‑detection. The original alpha channel LSBs are saved and can be restored (`--restore-container`).
4. **Media steganography:** Data bits are embedded into GIF frame pixels, MP4 YUV (U/V) planes, or MP3 audio samples.
5. **Scanning:** The program searches raw bytes for `V1|...` headers (direct mode) and all LSB layers (1–8 bits) across all channel combinations for the `0xCC0DE5` magic signature (III mode).

## Project structure

- `core.py` — encoding/decoding engine + CLI (performance, Image‑in‑Image, scanning)
- `gui.py` — Tkinter graphical interface (all features)
- `stego_media.py` — optional media steganography (GIF, MP4, MP3)