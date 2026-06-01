import os
import time
import hashlib
import base64
import zlib
import secrets
import json
import sys
import argparse
import platform
from pathlib import Path
from array import array
from threading import Event
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Random import get_random_bytes
from PIL import Image

CURRENT_VERSION = "1"

MODE_MONO = "mono"
MODE_RGB = "rgb"
MODE_RGBA = "rgba"

OUTPUT_FORMATS = {
    "PNG": "png",
    "WebP": "webp",
    "BMP": "bmp"
}

COMPRESS_LEVELS = {
    "none": 0,
    "min": 1,
    "normal": 6,
    "max": 9
}

ENCODE_MODES = {
    "base64": "base64",
    "raw": "raw"
}

CHUNK_SIZES = {
    "10MB": 10 * 1024 * 1024,
    "50MB": 50 * 1024 * 1024,
    "100MB": 100 * 1024 * 1024,
    "250MB": 250 * 1024 * 1024
}

class ColorCryptCore:

    def __init__(self, debug_callback=None, progress_callback=None):
        self.debug_callback = debug_callback
        self.progress_callback = progress_callback
        self.cancel_event = Event()

        self.compress_enabled = False
        self.compress_level = "normal"
        self.channel_mode = MODE_RGB
        self.integrity_enabled = True
        self.encryption_enabled = False
        self.password = None
        self.key = None
        self.salt = None
        self.output_format = "PNG"
        self.make_square = False
        self.output_dir = None
        self.encode_mode = "base64"
        self.chunk_mode = False
        self.chunk_size = "50MB"
        self.preserve_filename = True

    def _log_debug(self, message):
        if self.debug_callback:
            self.debug_callback(message)

    def _update_progress(self, current, total, message=""):
        if self.progress_callback:
            self.progress_callback(current, total, message)

    def set_settings(self, compress_enabled=False, compress_level="normal",
                     channel_mode=MODE_RGB, integrity_enabled=True,
                     encryption_enabled=False, password=None, key=None,
                     output_format="PNG", make_square=False, output_dir=None,
                     encode_mode="base64", chunk_mode=False, chunk_size="50MB",
                     preserve_filename=True):
        self.compress_enabled = compress_enabled
        self.compress_level = compress_level
        self.channel_mode = channel_mode
        self.integrity_enabled = integrity_enabled
        self.encryption_enabled = encryption_enabled
        self.password = password
        self.key = key
        self.output_format = output_format
        self.make_square = make_square
        self.output_dir = output_dir
        self.encode_mode = encode_mode
        self.chunk_mode = chunk_mode
        self.chunk_size = chunk_size
        self.preserve_filename = preserve_filename

    def generate_key_from_password(self, password, salt=None):
        if salt is None:
            salt = get_random_bytes(32)
        self.salt = salt
        key = PBKDF2(password, salt, dkLen=32, count=100000)
        return key, salt

    def encrypt_data_gcm(self, data):
        if not self.encryption_enabled:
            return data, None, None

        if self.key is None and self.password:
            self.key, self.salt = self.generate_key_from_password(self.password)
        elif self.key is None:
            raise ValueError("Ключ или пароль не установлены")

        if self.salt is None:
            self.salt = get_random_bytes(32)

        iv = get_random_bytes(12)
        cipher = AES.new(self.key, AES.MODE_GCM, nonce=iv)
        encrypted_data, tag = cipher.encrypt_and_digest(data)

        metadata = {
            'iv': base64.b64encode(iv).decode('ascii'),
            'tag': base64.b64encode(tag).decode('ascii'),
            'salt': base64.b64encode(self.salt).decode('ascii'),
            'mode': 'GCM'
        }
        metadata_json = json.dumps(metadata).encode('utf-8')
        metadata_b64 = base64.b64encode(metadata_json).decode('ascii')

        return encrypted_data, metadata_b64, self.salt

    def decrypt_data_gcm(self, encrypted_data, metadata_b64, password=None, key=None):
        try:
            metadata_json = base64.b64decode(metadata_b64)
            metadata = json.loads(metadata_json.decode('utf-8'))
            iv = base64.b64decode(metadata['iv'])
            tag = base64.b64decode(metadata['tag'])
            salt = base64.b64decode(metadata['salt'])

            if key:
                decrypt_key = key
            elif password:
                decrypt_key, _ = self.generate_key_from_password(password, salt)
            else:
                return None

            cipher = AES.new(decrypt_key, AES.MODE_GCM, nonce=iv)
            decrypted_data = cipher.decrypt_and_verify(encrypted_data, tag)
            return decrypted_data
        except Exception as e:
            self._log_debug(f"Ошибка дешифрования: {e}\n")
            return None

    def encrypt_data(self, data):
        return self.encrypt_data_gcm(data)

    def decrypt_data(self, encrypted_data, metadata_b64, password=None, key=None):
        return self.decrypt_data_gcm(encrypted_data, metadata_b64, password, key)

    def get_channels_count(self):
        if self.channel_mode == MODE_MONO:
            return 1
        elif self.channel_mode == MODE_RGB:
            return 3
        elif self.channel_mode == MODE_RGBA:
            return 4
        return 3

    def get_mode_char(self):
        if self.channel_mode == MODE_MONO:
            return 'M'
        elif self.channel_mode == MODE_RGB:
            return 'R'
        elif self.channel_mode == MODE_RGBA:
            return 'A'
        return 'R'

    def prepare_pixel_array(self, data_bytes, channels):
        total_bytes = len(data_bytes)

        if channels == 1:
            pixels = list(data_bytes)
            pixels_needed = total_bytes
        elif channels == 3:
            pixels = []
            for i in range(0, total_bytes, 3):
                if i + 2 < total_bytes:
                    pixels.append((data_bytes[i], data_bytes[i+1], data_bytes[i+2]))
                elif i + 1 < total_bytes:
                    pixels.append((data_bytes[i], data_bytes[i+1], 0))
                else:
                    pixels.append((data_bytes[i], 0, 0))
            pixels_needed = (total_bytes + 2) // 3
        else:
            pixels = []
            for i in range(0, total_bytes, 4):
                if i + 3 < total_bytes:
                    pixels.append((data_bytes[i], data_bytes[i+1], data_bytes[i+2], data_bytes[i+3]))
                elif i + 2 < total_bytes:
                    pixels.append((data_bytes[i], data_bytes[i+1], data_bytes[i+2], 255))
                elif i + 1 < total_bytes:
                    pixels.append((data_bytes[i], data_bytes[i+1], 0, 255))
                else:
                    pixels.append((data_bytes[i], 0, 0, 255))
            pixels_needed = (total_bytes + 3) // 4

        return pixels, pixels_needed

    def encode_chunked(self, full_data, output_dir, base_name, original_name):
        chunk_limit = CHUNK_SIZES.get(self.chunk_size, 50 * 1024 * 1024)
        chunks = []
        total = len(full_data)
        for i in range(0, total, chunk_limit):
            if self.cancel_event.is_set():
                return None
            chunk_data = full_data[i:i+chunk_limit]
            chunk_file = os.path.join(output_dir, f"{base_name}_chunk_{i//chunk_limit+1:04d}")
            result = self.encode_single(chunk_data, output_dir, chunk_file, original_name)
            if result['success']:
                chunks.append(result['output_path'])
            else:
                return None
        meta = {
            'file_name': original_name or base_name,
            'chunk_size': chunk_limit,
            'chunk_files': chunks,
            'total_chunks': len(chunks)
        }
        meta_path = os.path.join(output_dir, f"{base_name}_chunks_info.json")
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(meta, f, indent=2)
        return meta_path

    def encode_single(self, data, output_dir, base_name, original_name=None):
        start_time = time.time()
        result = {
            'success': False,
            'output_path': None,
            'width': 0,
            'height': 0,
            'size': 0,
            'sha256': None,
            'elapsed': 0,
            'error': None
        }

        try:
            channels = self.get_channels_count()
            mode_char = self.get_mode_char()

            if self.encode_mode == "base64":
                b64_data = base64.b64encode(data).decode('ascii')
                data_bytes = b64_data.encode('ascii')
            else:
                data_bytes = bytes(data)

            if self.compress_enabled:
                data_bytes = self.compress_data(data_bytes)

            encryption_metadata = None
            if self.encryption_enabled:
                encrypted_data, encryption_metadata, _ = self.encrypt_data(data_bytes)
                if encrypted_data:
                    data_bytes = encrypted_data

            header_parts = [
                f"V{CURRENT_VERSION}",
                "C" if self.compress_enabled else "N",
                mode_char,
                f"EM:{self.encode_mode}"
            ]

            if self.encryption_enabled and encryption_metadata:
                header_parts.append(f"ENC:{encryption_metadata}")

            if self.preserve_filename and original_name:
                header_parts.append(f"NAME:{original_name}")

            if self.integrity_enabled:
                sha = hashlib.sha256(data).hexdigest()
                header_parts.append(f"SHA256:{sha}")
                result['sha256'] = sha[:16] + "..."

            header_parts.append(f"LEN:{len(data_bytes)}")

            header = '|'.join(header_parts)
            header_bytes = header.encode('ascii')
            header_length = len(header_bytes)
            length_bytes = header_length.to_bytes(4, 'big')

            full_data = length_bytes + header_bytes + data_bytes
            total_bytes = len(full_data)

            pixels, pixels_needed = self.prepare_pixel_array(full_data, channels)

            img_width = min(pixels_needed, 4096)
            img_height = (pixels_needed + img_width - 1) // img_width

            if channels == 1:
                img = Image.new('L', (img_width, img_height), 0)
            elif channels == 4:
                img = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 255))
            else:
                img = Image.new('RGB', (img_width, img_height), (0, 0, 0))

            img.putdata(pixels)

            if output_dir is None:
                output_dir = self.output_dir or Path.cwd()
            os.makedirs(output_dir, exist_ok=True)

            ext = OUTPUT_FORMATS.get(self.output_format, "png")
            output = os.path.join(output_dir, f"{base_name}.{ext}")

            img.save(output, format=self.output_format, optimize=True)

            elapsed = time.time() - start_time

            result.update({
                'success': True,
                'output_path': output,
                'width': img_width,
                'height': img_height,
                'size': os.path.getsize(output),
                'elapsed': elapsed,
                'channels': channels,
                'encrypted': self.encryption_enabled,
                'total_bytes': total_bytes
            })

        except Exception as e:
            result['error'] = str(e)
            self._log_debug(f"Ошибка: {e}\n")

        return result

    def decode(self, input_file_path, output_dir=None, password=None, key=None):
        self.cancel_event.clear()

        if input_file_path.endswith('chunks_info.json'):
            return self._decode_chunked(input_file_path, output_dir, password, key)

        try:
            self._update_progress(10, 100, "Открытие изображения...")
            img = Image.open(input_file_path)

            if img.mode == 'L':
                channels = 1
            elif img.mode == 'RGB':
                channels = 3
            elif img.mode == 'RGBA':
                channels = 4
            else:
                channels = 3

            self._log_debug(f"Изображение: {img.size[0]}x{img.size[1]}, режим: {img.mode}\n")

            pixels = list(img.getdata())
            total_pixels = len(pixels)

            data_bytes = array('B')
            for i, pixel in enumerate(pixels):
                if self.cancel_event.is_set():
                    return {'success': False, 'error': 'Операция отменена'}
                if channels == 1:
                    if isinstance(pixel, int):
                        data_bytes.append(pixel)
                    else:
                        data_bytes.append(pixel[0])
                elif channels == 3:
                    data_bytes.append(pixel[0])
                    data_bytes.append(pixel[1])
                    data_bytes.append(pixel[2])
                else:
                    data_bytes.append(pixel[0])
                    data_bytes.append(pixel[1])
                    data_bytes.append(pixel[2])
                    data_bytes.append(pixel[3])
                if i % 10000 == 0:
                    self._update_progress(30 + (i*70)//total_pixels, 100, "Чтение данных...")

            self._update_progress(30, 100, "Чтение данных...")

            if len(data_bytes) < 4:
                raise ValueError("Файл слишком мал или повреждён")

            header_length = int.from_bytes(bytes(data_bytes[:4]), 'big')

            if header_length + 4 > len(data_bytes):
                self._log_debug("Попытка декодирования в старом формате...\n")
                return self._decode_legacy(data_bytes, img, output_dir, password, key)

            header_bytes = bytes(data_bytes[4:4+header_length])
            payload_bytes = bytes(data_bytes[4+header_length:])

            try:
                header = header_bytes.decode('ascii')
            except UnicodeDecodeError:
                raise ValueError("Неверный формат заголовка")

            self._log_debug(f"Заголовок: {header[:200]}...\n")

            compressed = False
            encode_mode = "base64"
            encryption_metadata = None
            sha256 = None
            expected_len = None
            original_name = None

            parts = header.split('|')
            for part in parts:
                if part == 'C':
                    compressed = True
                elif part == 'N':
                    compressed = False
                elif part.startswith('EM:'):
                    encode_mode = part[3:]
                elif part.startswith('ENC:'):
                    encryption_metadata = part[4:]
                elif part.startswith('SHA256:'):
                    sha256 = part[7:]
                elif part.startswith('LEN:'):
                    expected_len = int(part[4:])
                elif part.startswith('NAME:'):
                    original_name = part[5:]

            if expected_len is not None and expected_len < len(payload_bytes):
                payload_bytes = payload_bytes[:expected_len]

            data_to_process = payload_bytes

            if encryption_metadata:
                self._update_progress(60, 100, "Расшифровка...")
                decrypted = self.decrypt_data_gcm(data_to_process, encryption_metadata, password, key)
                if decrypted is None:
                    raise ValueError("Неверный пароль или повреждённые данные")
                data_to_process = decrypted

            if compressed:
                self._update_progress(70, 100, "Распаковка...")
                data_to_process = self.decompress_data(data_to_process)

            self._update_progress(80, 100, "Финальная обработка...")
            if encode_mode == "base64":
                final_data = base64.b64decode(data_to_process)
            else:
                final_data = data_to_process

            if sha256 and self.integrity_enabled:
                calc_sha = hashlib.sha256(final_data).hexdigest()
                if calc_sha != sha256:
                    self._log_debug(f"⚠️ SHA-256 не совпадает!\n")
                else:
                    self._log_debug(f"✅ SHA-256 совпадает\n")

            if output_dir is None:
                output_dir = self.output_dir or os.path.dirname(input_file_path)
            os.makedirs(output_dir, exist_ok=True)

            if original_name:
                output = os.path.join(output_dir, original_name)
            else:
                output = os.path.join(output_dir, f"decoded_{int(time.time())}")

            with open(output, 'wb') as f:
                f.write(final_data)

            self._update_progress(100, 100, "Готово!")

            return {
                'success': True,
                'output_path': output,
                'size': len(final_data),
                'elapsed': 0
            }

        except Exception as e:
            self._log_debug(f"Ошибка: {e}\n")
            return {'success': False, 'error': str(e)}

    def _decode_legacy(self, data_bytes, img, output_dir, password, key):
        try:
            try:
                sep_index = data_bytes.index(0)
                header_bytes = data_bytes[:sep_index]
                payload_bytes = data_bytes[sep_index + 1:]
            except ValueError:
                header_bytes = data_bytes
                payload_bytes = array('B')

            header = bytes(header_bytes).decode('ascii', errors='ignore')
            self._log_debug(f"Legacy заголовок: {header[:200]}...\n")

            compressed = False
            encode_mode = "base64"
            encryption_metadata = None
            sha256 = None
            expected_len = None

            parts = header.split('|')
            for part in parts:
                if part == 'C':
                    compressed = True
                elif part == 'N':
                    compressed = False
                elif part.startswith('EM:'):
                    encode_mode = part[3:]
                elif part.startswith('ENC:'):
                    encryption_metadata = part[4:]
                elif part.startswith('SHA256:'):
                    sha256 = part[7:]
                elif part.startswith('LEN:'):
                    expected_len = int(part[4:])

            data_to_process = bytes(payload_bytes)
            if expected_len is not None and expected_len < len(data_to_process):
                data_to_process = data_to_process[:expected_len]

            if encryption_metadata:
                decrypted = self.decrypt_data_gcm(data_to_process, encryption_metadata, password, key)
                if decrypted is None:
                    raise ValueError("Неверный пароль или повреждённые данные")
                data_to_process = decrypted

            if compressed:
                data_to_process = self.decompress_data(data_to_process)

            if encode_mode == "base64":
                final_data = base64.b64decode(data_to_process)
            else:
                final_data = data_to_process

            if output_dir is None:
                output_dir = self.output_dir or os.path.dirname('.')
            os.makedirs(output_dir, exist_ok=True)

            output = os.path.join(output_dir, f"decoded_legacy_{int(time.time())}")

            with open(output, 'wb') as f:
                f.write(final_data)

            return {
                'success': True,
                'output_path': output,
                'size': len(final_data),
                'elapsed': 0
            }

        except Exception as e:
            return {'success': False, 'error': f"Legacy decode failed: {e}"}

    def _decode_chunked(self, info_file, output_dir, password, key):
        with open(info_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        chunk_files = metadata['chunk_files']
        all_data = bytearray()

        for i, chunk_file in enumerate(chunk_files):
            if self.cancel_event.is_set():
                return {'success': False, 'error': 'Операция отменена'}

            if not os.path.exists(chunk_file):
                continue

            result = self.decode(chunk_file, output_dir, password, key)

            if result['success']:
                with open(result['output_path'], 'rb') as f:
                    chunk_data = f.read()
                    all_data.extend(chunk_data)
                progress = int((i / len(chunk_files)) * 100)
                self._update_progress(progress, 100, f"Декодирование чанка {i+1}/{len(chunk_files)}")

        if output_dir is None:
            output_dir = self.output_dir or os.path.dirname(info_file)
        os.makedirs(output_dir, exist_ok=True)

        original_name = metadata.get('file_name', 'restored_file')
        output = os.path.join(output_dir, original_name)

        with open(output, 'wb') as f:
            f.write(all_data)

        return {
            'success': True,
            'output_path': output,
            'size': len(all_data),
            'chunked': True,
            'num_chunks': len(chunk_files)
        }

    def compress_data(self, data):
        if not self.compress_enabled:
            return data

        level = COMPRESS_LEVELS.get(self.compress_level, 6)
        start_time = time.time()

        compressed = zlib.compress(data, level)
        ratio = (1 - len(compressed) / len(data)) * 100 if len(data) > 0 else 0

        self._log_debug(f"Сжатие: {len(data)} → {len(compressed)} байт (-{ratio:.1f}%)\n")
        return compressed

    def decompress_data(self, data):
        if not data:
            return data
        try:
            return zlib.decompress(data)
        except:
            return data

    def encode(self, input_file_path, output_dir=None, output_name=None):
        self.cancel_event.clear()

        with open(input_file_path, 'rb') as f:
            data = f.read()

        self._update_progress(10, 100, "Файл прочитан")

        if output_name is None:
            basename = os.path.splitext(os.path.basename(input_file_path))[0]
            output_name = basename

        original_filename = os.path.basename(input_file_path) if self.preserve_filename else None

        if self.chunk_mode and len(data) > CHUNK_SIZES.get(self.chunk_size, 50*1024*1024):
            self._update_progress(20, 100, "Разделение на чанки...")
            meta_path = self.encode_chunked(data, output_dir or self.output_dir or os.path.dirname(input_file_path), output_name, original_filename)
            if meta_path:
                return {'success': True, 'output_path': meta_path, 'chunked': True}
            else:
                return {'success': False, 'error': 'Ошибка чанкового кодирования'}

        result = self.encode_single(data, output_dir, output_name, original_filename)
        return result

    def cancel(self):
        self.cancel_event.set()

    def batch_encode(self, file_list, output_dir=None):
        results = []
        for i, filepath in enumerate(file_list):
            if self.cancel_event.is_set():
                break
            self._update_progress(i, len(file_list), f"Кодирование {os.path.basename(filepath)}")
            out_name = os.path.splitext(os.path.basename(filepath))[0]
            result = self.encode(filepath, output_dir, out_name)
            results.append(result)
        return results

    def batch_decode(self, file_list, output_dir=None, password=None):
        results = []
        for i, filepath in enumerate(file_list):
            if self.cancel_event.is_set():
                break
            self._update_progress(i, len(file_list), f"Декодирование {os.path.basename(filepath)}")
            result = self.decode(filepath, output_dir, password)
            results.append(result)
        return results

    def check_encryption(self, filepath):
        try:
            img = Image.open(filepath)
            if img.mode == 'L':
                channels = 1
            elif img.mode == 'RGB':
                channels = 3
            elif img.mode == 'RGBA':
                channels = 4
            else:
                channels = 3
            pixels = list(img.getdata())
            data_bytes = array('B')
            max_bytes = 4096
            for pixel in pixels:
                if channels == 1:
                    if isinstance(pixel, int):
                        data_bytes.append(pixel)
                    else:
                        data_bytes.append(pixel[0])
                elif channels == 3:
                    data_bytes.append(pixel[0])
                    data_bytes.append(pixel[1])
                    data_bytes.append(pixel[2])
                else:
                    data_bytes.append(pixel[0])
                    data_bytes.append(pixel[1])
                    data_bytes.append(pixel[2])
                    data_bytes.append(pixel[3])
                if len(data_bytes) >= max_bytes:
                    break
            if len(data_bytes) < 4:
                return False
            header_length = int.from_bytes(bytes(data_bytes[:4]), 'big')
            if header_length + 4 > len(data_bytes):
                return False
            header_bytes = bytes(data_bytes[4:4+header_length])
            try:
                header = header_bytes.decode('ascii', errors='ignore')
                return 'ENC:' in header
            except:
                return False
        except:
            return False

def main_cli():
    import argparse
    parser = argparse.ArgumentParser(description='ColorCrypt')
    parser.add_argument('mode', choices=['encode', 'decode'])
    parser.add_argument('input')
    parser.add_argument('-o', '--output')
    parser.add_argument('-p', '--password')
    parser.add_argument('-c', '--compress', choices=['none', 'min', 'normal', 'max'], default='normal')
    parser.add_argument('-m', '--mode', choices=['mono', 'rgb', 'rgba'], default='rgb')
    parser.add_argument('--encode-mode', choices=['base64', 'raw'], default='base64')
    parser.add_argument('--no-integrity', action='store_true')
    parser.add_argument('--format', choices=['PNG', 'WebP', 'BMP'], default='PNG')
    parser.add_argument('--chunk', action='store_true')
    parser.add_argument('--chunk-size', choices=['10MB', '50MB', '100MB', '250MB'], default='50MB')
    parser.add_argument('--no-preserve-name', action='store_true', help='Не сохранять оригинальное имя файла')

    args = parser.parse_args()

    core = ColorCryptCore()
    core.set_settings(
        compress_enabled=args.compress != 'none',
        compress_level=args.compress,
        channel_mode=args.mode,
        integrity_enabled=not args.no_integrity,
        encryption_enabled=bool(args.password),
        password=args.password,
        output_format=args.format,
        encode_mode=args.encode_mode,
        chunk_mode=args.chunk,
        chunk_size=args.chunk_size,
        preserve_filename=not args.no_preserve_name
    )

    if args.mode == 'encode':
        output_dir = None
        output_name = None
        if args.output:
            if os.path.isdir(args.output):
                output_dir = args.output
            else:
                output_dir = os.path.dirname(args.output) or '.'
                output_name = os.path.splitext(os.path.basename(args.output))[0]
        result = core.encode(args.input, output_dir, output_name)
        if result['success']:
            print(f"✅ Успех! {result['output_path']}")
        else:
            print(f"❌ Ошибка: {result.get('error')}")
            sys.exit(1)
    else:
        output_dir = None
        if args.output:
            if os.path.isdir(args.output):
                output_dir = args.output
            else:
                output_dir = os.path.dirname(args.output) or '.'
        result = core.decode(args.input, output_dir, password=args.password)
        if result['success']:
            print(f"✅ Успех! {result['output_path']}")
        else:
            print(f"❌ Ошибка: {result.get('error')}")
            sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        main_cli()
    else:
        try:
            import tkinter as tk
            from gui import main
            main()
        except ImportError:
            print("Используйте CLI режим: python core.py encode input.txt -o output.png")