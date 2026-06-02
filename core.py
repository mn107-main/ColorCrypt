import os
import time
import hashlib
import base64
import zlib
import json
import sys
import argparse
from pathlib import Path
from array import array
from threading import Event
from functools import lru_cache
import numpy as np
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
    "BMP": "bmp",
    "TIFF": "tiff"
}

COMPRESS_LEVELS = {
    "none": 0,
    "min": 1,
    "normal": 6,
    "max": 9
}

ENCODE_MODES = {
    "base64": "base64"
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
        self.lsb_bits = 0

        self._data_cache = {}

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
                     preserve_filename=True, lsb_bits=0):
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
        self.lsb_bits = lsb_bits

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
            arr = np.frombuffer(data_bytes, dtype=np.uint8)
            remainder = total_bytes % 3
            if remainder:
                pad = 3 - remainder
                arr = np.pad(arr, (0, pad), constant_values=0)
            pixels = list(map(tuple, arr.reshape(-1, 3)))
            pixels_needed = (total_bytes + 2) // 3
        else:
            arr = np.frombuffer(data_bytes, dtype=np.uint8)
            remainder = total_bytes % 4
            if remainder:
                pad = 4 - remainder
                arr = np.pad(arr, (0, pad), constant_values=0)
            arr = arr.reshape(-1, 4)
            if remainder:
                arr[-1, 3] = 255
            pixels = list(map(tuple, arr))
            pixels_needed = (total_bytes + 3) // 4

        return pixels, pixels_needed

    def _decode_lsb_payload(self, data_bytes, start_offset, lsb):
        remaining = data_bytes[start_offset:]
        if lsb == 1:
            extracted_bits = remaining & 1
        elif lsb == 2:
            vals = remaining & 0x03
            extracted_bits = np.zeros(len(vals) * 2, dtype=np.uint8)
            extracted_bits[0::2] = vals & 1
            extracted_bits[1::2] = (vals >> 1) & 1
        elif lsb == 3:
            vals = remaining & 0x07
            extracted_bits = np.zeros(len(vals) * 3, dtype=np.uint8)
            extracted_bits[0::3] = vals & 1
            extracted_bits[1::3] = (vals >> 1) & 1
            extracted_bits[2::3] = (vals >> 2) & 1
        elif lsb == 4:
            vals = remaining & 0x0F
            extracted_bits = np.zeros(len(vals) * 4, dtype=np.uint8)
            extracted_bits[0::4] = vals & 1
            extracted_bits[1::4] = (vals >> 1) & 1
            extracted_bits[2::4] = (vals >> 2) & 1
            extracted_bits[3::4] = (vals >> 3) & 1
        else:
            return bytes(remaining)
        return np.packbits(extracted_bits).tobytes()

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

            b64_data = base64.b64encode(data).decode('ascii')
            data_bytes = b64_data.encode('ascii')

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

            if self.lsb_bits > 0:
                header_parts.append(f"LSB:{self.lsb_bits}")

            header_parts.append(f"LEN:{len(data_bytes)}")

            header = '|'.join(header_parts)
            header_bytes = header.encode('ascii')
            header_length = len(header_bytes)
            length_bytes = header_length.to_bytes(4, 'big')

            full_data = length_bytes + header_bytes + data_bytes
            total_bytes = len(full_data)

            if self.lsb_bits > 0:
                lsb = self.lsb_bits
                header_byte_count = 4 + len(header_bytes)
                header_data = full_data[:header_byte_count]
                payload_data = full_data[header_byte_count:]
                payload_bits = np.unpackbits(np.frombuffer(payload_data, dtype=np.uint8))

                header_channels_needed = header_byte_count
                payload_channels_needed = (len(payload_bits) + lsb - 1) // lsb
                total_channels_needed = header_channels_needed + payload_channels_needed
                pixels_needed = (total_channels_needed + channels - 1) // channels

                img_width = min(pixels_needed, 4096)
                img_height = (pixels_needed + img_width - 1) // img_width

                if channels == 1:
                    img = Image.new('L', (img_width, img_height), 0)
                elif channels == 4:
                    img = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 255))
                else:
                    img = Image.new('RGB', (img_width, img_height), (0, 0, 0))

                flat = np.array(img, dtype=np.uint8).reshape(-1)

                flat[:header_channels_needed] = np.frombuffer(header_data, dtype=np.uint8)

                chunk = flat[header_channels_needed:header_channels_needed + payload_channels_needed]
                if lsb == 1:
                    chunk = (chunk & 0xFE) | payload_bits[:len(chunk)]
                elif lsb == 2:
                    paired = payload_bits[0::2].astype(np.uint16) | (payload_bits[1::2].astype(np.uint16) << 1)
                    chunk = (chunk & 0xFC) | paired[:len(chunk)].astype(np.uint8)
                elif lsb == 3:
                    triple = (payload_bits[0::3].astype(np.uint16) |
                              (payload_bits[1::3].astype(np.uint16) << 1) |
                              (payload_bits[2::3].astype(np.uint16) << 2))
                    chunk = (chunk & 0xF8) | triple[:len(chunk)].astype(np.uint8)
                elif lsb == 4:
                    quad = (payload_bits[0::4].astype(np.uint16) |
                            (payload_bits[1::4].astype(np.uint16) << 1) |
                            (payload_bits[2::4].astype(np.uint16) << 2) |
                            (payload_bits[3::4].astype(np.uint16) << 3))
                    chunk = (chunk & 0xF0) | quad[:len(chunk)].astype(np.uint8)
                flat[header_channels_needed:header_channels_needed + payload_channels_needed] = chunk

                img = Image.fromarray(flat.reshape(img_height, img_width, channels) if channels > 1 else flat.reshape(img_height, img_width))
            else:
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

            save_kwargs = {'format': self.output_format}
            if self.output_format == 'WebP':
                save_kwargs['lossless'] = True
            else:
                save_kwargs['optimize'] = True
            img.save(output, **save_kwargs)

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

            arr = np.array(img, dtype=np.uint8)
            if self.cancel_event.is_set():
                return {'success': False, 'error': 'Операция отменена'}

            data_bytes = arr.reshape(-1)

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
            lsb_bits = 0

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
                elif part.startswith('LSB:'):
                    lsb_bits = int(part[4:])

            if lsb_bits > 0:
                header_byte_count = 4 + header_length
                payload_bytes = self._decode_lsb_payload(data_bytes, header_byte_count, lsb_bits)

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
            final_data = base64.b64decode(data_to_process)

            if sha256 and self.integrity_enabled:
                calc_sha = hashlib.sha256(final_data).hexdigest()
                if calc_sha != sha256:
                    self._log_debug(f"⚠️ SHA-256 не совпадает!\n")
                else:
                    self._log_debug(f"✅ SHA-256 совпадает\n")

            if output_dir is None:
                output_dir = self.output_dir or str(Path.cwd())
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
            if isinstance(data_bytes, np.ndarray):
                data_list = data_bytes.tolist()
                try:
                    sep_index = data_list.index(0)
                    header_bytes = array('B', data_list[:sep_index])
                    payload_bytes = array('B', data_list[sep_index + 1:])
                except ValueError:
                    header_bytes = array('B', data_list)
                    payload_bytes = array('B')
            else:
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

            final_data = base64.b64decode(data_to_process)

            if sha256 and self.integrity_enabled:
                calc_sha = hashlib.sha256(final_data).hexdigest()
                if calc_sha != sha256:
                    self._log_debug(f"⚠️ Legacy SHA-256 не совпадает!\n")
                else:
                    self._log_debug(f"✅ Legacy SHA-256 совпадает\n")

            if output_dir is None:
                output_dir = self.output_dir or str(Path.cwd())
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
        temp_decoded = []

        try:
            for i, chunk_file in enumerate(chunk_files):
                if self.cancel_event.is_set():
                    return {'success': False, 'error': 'Операция отменена'}

                if not os.path.exists(chunk_file):
                    raise FileNotFoundError(f"Отсутствует чанк: {chunk_file}")

                result = self.decode(chunk_file, output_dir, password, key)

                if result['success']:
                    temp_decoded.append(result['output_path'])
                    with open(result['output_path'], 'rb') as f:
                        chunk_data = f.read()
                        all_data.extend(chunk_data)
                    progress = int((i / len(chunk_files)) * 100)
                    self._update_progress(progress, 100, f"Декодирование чанка {i+1}/{len(chunk_files)}")

            if output_dir is None:
                output_dir = self.output_dir or str(Path(info_file).parent)
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
        finally:
            for path in temp_decoded:
                try:
                    os.remove(path)
                except Exception:
                    pass

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
        except Exception as e:
            self._log_debug(f"Ошибка декомпрессии: {e}\n")
            raise

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
                flat = np.array(img, dtype=np.uint8).ravel()
            elif img.mode == 'RGB':
                flat = np.array(img, dtype=np.uint8).reshape(-1)
            elif img.mode == 'RGBA':
                flat = np.array(img, dtype=np.uint8).reshape(-1)
            else:
                flat = np.array(img.convert('RGB'), dtype=np.uint8).reshape(-1)
            data_bytes = flat[:4096]
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

    # ─── Image-in-Image Steganography ───────────────────────────────────

    MAGIC_SIG = b'\xCC\x0D\xE5'
    III_VERSION = b'\x01'
    III_VERSION_ALPHA = b'\x02'

    def encode_image_in_image(self, container_path, secret_path, output_path, use_alpha=True):
        try:
            container = Image.open(container_path).convert('RGBA')
            secret = Image.open(secret_path)
            cw, ch = container.size

            secret = secret.convert('L')
            sw, sh = secret.size

            if sw > cw or sh > ch:
                canvas = Image.new('L', (cw, ch), 0)
                canvas.paste(secret, (0, 0))
                secret = canvas
                sw, sh = secret.size

            secret_bytes = secret.tobytes()
            compressed = zlib.compress(secret_bytes)

            container_arr = np.array(container, dtype=np.uint8)
            flat = container_arr.reshape(-1, 4)

            compressed_alpha = b''
            header_version = self.III_VERSION

            if use_alpha:
                orig_alpha_lsb = (flat[:, 3] & 1).astype(np.uint8)
                compressed_alpha = zlib.compress(np.packbits(orig_alpha_lsb).tobytes())
                header_version = self.III_VERSION_ALPHA

            alpha_len = len(compressed_alpha)

            header = self.MAGIC_SIG + header_version
            header += sw.to_bytes(4, 'big') + sh.to_bytes(4, 'big')
            header += len(compressed).to_bytes(4, 'big')
            header += alpha_len.to_bytes(4, 'big')

            data_to_hide = header + compressed + compressed_alpha
            total_bits = len(data_to_hide) * 8

            if use_alpha:
                bits_per_pixel = 1
            else:
                bits_per_pixel = 3

            needed_pixels = (total_bits + bits_per_pixel - 1) // bits_per_pixel
            if needed_pixels > cw * ch:
                raise ValueError(f"Контейнер слишком мал: нужно {needed_pixels} пикселей, есть {cw*ch}")

            data_bits = np.unpackbits(np.frombuffer(data_to_hide, dtype=np.uint8))

            if use_alpha:
                alpha_view = flat[:, 3]
                for i in range(min(len(data_bits), len(alpha_view))):
                    alpha_view[i] = (alpha_view[i] & 0xFE) | int(data_bits[i])
            else:
                for i in range(min(len(data_bits), len(flat) * 3)):
                    px_idx = i // 3
                    ch_idx = i % 3
                    flat[px_idx, ch_idx] = (flat[px_idx, ch_idx] & 0xFE) | int(data_bits[i])

            result = Image.fromarray(container_arr, 'RGBA')
            result.save(output_path, format='PNG', optimize=True)

            return {
                'success': True,
                'output_path': output_path,
                'secret_size': (sw, sh),
                'container_size': (cw, ch),
                'alpha_preserved': use_alpha
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def decode_image_in_image(self, image_path, output_path, use_alpha=True, restore_container=False):
        try:
            img = Image.open(image_path).convert('RGBA')
            arr = np.array(img, dtype=np.uint8)
            flat = arr.reshape(-1, 4)

            max_bits = 20 * 8 + 8

            if use_alpha:
                alpha_bits = flat[:, 3] & 1
                bits = alpha_bits
            else:
                rgb_bits = flat[:, :3].ravel() & 1
                bits = rgb_bits

            sig_bits = bits[:len(self.MAGIC_SIG) * 8].astype(np.uint8)
            sig_bytes = np.packbits(sig_bits).tobytes()

            if sig_bytes[:3] != self.MAGIC_SIG:
                return {'success': False, 'error': 'Сигнатура не найдена. Возможно, изображение не содержит скрытого изображения.'}

            offset = len(self.MAGIC_SIG) * 8
            ver_bits = bits[offset:offset + 8]
            offset += 8
            ver = int.from_bytes(np.packbits(ver_bits).tobytes(), 'big')

            w_bits = bits[offset:offset + 32]
            offset += 32
            h_bits = bits[offset:offset + 32]
            offset += 32
            secret_len_bits = bits[offset:offset + 32]
            offset += 32

            sw = int.from_bytes(np.packbits(w_bits).tobytes(), 'big')
            sh = int.from_bytes(np.packbits(h_bits).tobytes(), 'big')
            compressed_len = int.from_bytes(np.packbits(secret_len_bits).tobytes(), 'big')

            alpha_len = 0
            if ver >= 2:
                alpha_len_bits = bits[offset:offset + 32]
                offset += 32
                alpha_len = int.from_bytes(np.packbits(alpha_len_bits).tobytes(), 'big')

            if offset + compressed_len * 8 > len(bits):
                return {'success': False, 'error': 'Недостаточно данных в изображении'}

            data_bits = bits[offset:offset + compressed_len * 8]
            compressed_data = np.packbits(data_bits.astype(np.uint8)).tobytes()[:compressed_len]
            offset += compressed_len * 8

            compressed_alpha = b''
            if alpha_len > 0:
                if offset + alpha_len * 8 > len(bits):
                    return {'success': False, 'error': 'Недостаточно данных для альфа-восстановления'}
                alpha_data_bits = bits[offset:offset + alpha_len * 8]
                compressed_alpha = np.packbits(alpha_data_bits.astype(np.uint8)).tobytes()[:alpha_len]

            secret_bytes = zlib.decompress(compressed_data)
            secret_img = Image.frombytes('L', (sw, sh), secret_bytes)
            secret_img.save(output_path)

            result = {
                'success': True,
                'output_path': output_path,
                'secret_size': (sw, sh),
                'alpha_preserved': alpha_len > 0
            }

            if compressed_alpha and use_alpha and restore_container:
                try:
                    orig_lsb_bytes = zlib.decompress(compressed_alpha)
                    orig_lsb_bits = np.unpackbits(np.frombuffer(orig_lsb_bytes, dtype=np.uint8))
                    restore_count = min(len(orig_lsb_bits), len(alpha_bits))
                    flat[:restore_count, 3] = (flat[:restore_count, 3] & 0xFE) | orig_lsb_bits[:restore_count]
                    restored = Image.fromarray(arr, 'RGBA')
                    container_out = os.path.splitext(output_path)[0] + "_container_restored.png"
                    restored.save(container_out, format='PNG', optimize=True)
                    result['restored_container'] = container_out
                except Exception as e:
                    self._log_debug(f"Не удалось восстановить альфа-канал: {e}\n")

            return result
        except Exception as e:
            return {'success': False, 'error': str(e)}

    # ─── Header Scanning ────────────────────────────────────────────────

    def scan_for_header(self, filepath, scan_alpha=True, scan_rgb=True, max_layers=4):
        results = []
        try:
            img = Image.open(filepath)
            img_rgba = img.convert('RGBA')
            arr_rgba = np.array(img_rgba, dtype=np.uint8)
            flat_rgba = arr_rgba.reshape(-1, 4)
            num_pixels = flat_rgba.shape[0]

            raw_flat = np.array(img, dtype=np.uint8).reshape(-1)
            if len(raw_flat) > 4:
                hdr_len = int.from_bytes(bytes(raw_flat[:4]), 'big')
                if 4 < hdr_len < 2048 and hdr_len + 4 <= len(raw_flat):
                    hdr_bytes = bytes(raw_flat[4:4+hdr_len])
                    if hdr_bytes.startswith(b'V') and b'|' in hdr_bytes:
                        hdr_text = hdr_bytes.decode('ascii', errors='replace')
                        results.append({
                            'channel': 'raw',
                            'bits': 0,
                            'header': {'type': 'main', 'signature': hdr_text[:60], 'version': 1}
                        })

            channels_to_scan = []
            if scan_alpha:
                channels_to_scan.append(('A', 3))
            if scan_rgb:
                for name, idx in [('R', 0), ('G', 1), ('B', 2)]:
                    channels_to_scan.append((name, idx))
                channels_to_scan.append(('RGB', None))

            for ch_name, ch_idx in channels_to_scan:
                for bit_depth in range(1, max_layers + 1):
                    mask = (1 << bit_depth) - 1
                    if ch_idx is not None:
                        channel_bits = (flat_rgba[:, ch_idx] & mask)
                        recovered = self._try_extract_sig(channel_bits, bit_depth, num_pixels)
                    else:
                        r_bits = flat_rgba[:, 0] & mask
                        g_bits = (flat_rgba[:, 1] & mask) << bit_depth
                        b_bits = (flat_rgba[:, 2] & mask) << (bit_depth * 2)
                        combined = r_bits | g_bits | b_bits
                        recovered = self._try_extract_sig_ext(combined, bit_depth, num_pixels)

                    if recovered:
                        results.append({
                            'channel': ch_name,
                            'bits': bit_depth,
                            'header': recovered
                        })

            return results
        except Exception as e:
            return []

    def _extract_bytes_from_bits(self, bit_data, num_bytes):
        byte_count = min(num_bytes, len(bit_data) // 8)
        result = b''
        for i in range(byte_count):
            byte = 0
            for j in range(8):
                idx = i * 8 + j
                if idx < len(bit_data):
                    byte = (byte << 1) | (int(bit_data[idx]) & 1)
            result += bytes([byte])
        return result

    def _try_extract_sig(self, bit_data, bit_depth, num_pixels):
        sig_bytes = self._extract_bytes_from_bits(bit_data, 8)
        if sig_bytes[:3] == self.MAGIC_SIG:
            ver = int(sig_bytes[3]) if len(sig_bytes) > 3 else 1
            return {'type': 'iii', 'signature': sig_bytes[:3].hex(), 'version': ver}
        if sig_bytes.startswith(b'V'):
            return {'type': 'main', 'signature': 'V1|...', 'version': 1}
        return None

    def _try_extract_sig_ext(self, bit_data, bit_depth, num_pixels):
        sig_bytes = self._extract_bytes_from_bits(bit_data, 8)
        if sig_bytes[:3] == self.MAGIC_SIG:
            ver = int(sig_bytes[3]) if len(sig_bytes) > 3 else 1
            return {'type': 'iii', 'signature': sig_bytes[:3].hex(), 'version': ver}
        if sig_bytes.startswith(b'V'):
            return {'type': 'main', 'signature': 'V1|...', 'version': 1}
        return None


def _safe_print(msg):
    try:
        print(msg)
    except UnicodeEncodeError:
        safe = msg.encode('ascii', errors='replace').decode('ascii')
        print(safe)


def main_cli():
    import argparse
    parser = argparse.ArgumentParser(description='ColorCrypt')
    parser.add_argument('mode', choices=['encode', 'decode', 'iii-encode', 'iii-decode', 'scan'])
    parser.add_argument('input')
    parser.add_argument('input2', nargs='?', help='Второй входной файл (для iii-encode: секретное изображение)')
    parser.add_argument('-o', '--output')
    parser.add_argument('-p', '--password')
    parser.add_argument('-c', '--compress', choices=['none', 'min', 'normal', 'max'], default='normal')
    parser.add_argument('--channel-mode', choices=['mono', 'rgb', 'rgba'], default='rgb',
                        help='Цветовой режим: mono, rgb, rgba')
    parser.add_argument('--encode-mode', choices=['base64'], default='base64')
    parser.add_argument('--no-integrity', action='store_true')
    parser.add_argument('--format', choices=['PNG', 'WebP', 'BMP', 'TIFF'], default='PNG')
    parser.add_argument('--chunk', action='store_true')
    parser.add_argument('--chunk-size', choices=['10MB', '50MB', '100MB', '250MB'], default='50MB')
    parser.add_argument('--no-preserve-name', action='store_true', help='Не сохранять оригинальное имя файла')
    parser.add_argument('--lsb-bits', type=int, default=0, choices=[0, 1, 2, 3, 4],
                        help='LSB-битность для основного режима (0 = прямой, 1-4 = LSB)')
    parser.add_argument('--no-alpha', action='store_true', help='Для iii: не использовать альфа-канал')
    parser.add_argument('--restore-container', action='store_true', help='Для iii-decode: восстановить альфа-канал контейнера')
    parser.add_argument('--scan-alpha', action='store_true', default=True, help='Сканировать альфа-канал')
    parser.add_argument('--scan-rgb', action='store_true', default=True, help='Сканировать RGB-каналы')
    parser.add_argument('--scan-layers', type=int, default=4, help='Максимум LSB-слоёв для сканирования')

    args = parser.parse_args()

    core = ColorCryptCore()
    core.set_settings(
        compress_enabled=args.compress != 'none',
        compress_level=args.compress,
        channel_mode=args.channel_mode,
        integrity_enabled=not args.no_integrity,
        encryption_enabled=bool(args.password),
        password=args.password,
        output_format=args.format,
        encode_mode=args.encode_mode,
        chunk_mode=args.chunk,
        chunk_size=args.chunk_size,
        preserve_filename=not args.no_preserve_name,
        lsb_bits=args.lsb_bits
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
            _safe_print(f"Uspekh! {result['output_path']}")
        else:
            _safe_print(f"Oshibka: {result.get('error')}")
            sys.exit(1)
    elif args.mode == 'decode':
        output_dir = None
        explicit_name = None
        if args.output:
            if os.path.isdir(args.output):
                output_dir = args.output
            else:
                output_dir = os.path.dirname(args.output) or '.'
                explicit_name = os.path.basename(args.output)
        result = core.decode(args.input, output_dir, password=args.password)
        if result.get('success') and explicit_name:
            src = result['output_path']
            dst = os.path.join(os.path.dirname(src) or '.', explicit_name)
            if src != dst:
                import shutil
                shutil.move(src, dst)
                result['output_path'] = dst
        if result['success']:
            _safe_print(f"Uspekh! {result['output_path']}")
        else:
            _safe_print(f"Oshibka: {result.get('error')}")
            sys.exit(1)
    elif args.mode == 'iii-encode':
        if not args.input2:
            _safe_print("Oshibka: ukazhite sekretnoe izobrazhenie vtorim argumentom")
            sys.exit(1)
        output = args.output or f"iii_encoded_{int(time.time())}.png"
        result = core.encode_image_in_image(args.input, args.input2, output, use_alpha=not args.no_alpha)
        if result['success']:
            _safe_print(f"Image-in-Image kodirovanie zaversheno!")
            _safe_print(f"Sohraneno: {result['output_path']}")
            _safe_print(f"Razmer sekreta: {result['secret_size']}")
            if result.get('alpha_preserved'):
                _safe_print("Alpha-kanal sohranen")
        else:
            _safe_print(f"Oshibka: {result.get('error')}")
            sys.exit(1)
    elif args.mode == 'iii-decode':
        output = args.output or f"iii_decoded_{int(time.time())}.png"
        result = core.decode_image_in_image(args.input, output, use_alpha=not args.no_alpha, restore_container=args.restore_container)
        if result['success']:
            _safe_print(f"Image-in-Image dekodirovanie zaversheno!")
            _safe_print(f"Sohraneno: {result['output_path']}")
            _safe_print(f"Razmer sekreta: {result['secret_size']}")
            if result.get('restored_container'):
                _safe_print(f"Konterjner vosstanovlen: {result['restored_container']}")
        else:
            _safe_print(f"Oshibka: {result.get('error')}")
            sys.exit(1)
    elif args.mode == 'scan':
        _safe_print(f"Skanirovanie: {args.input}")
        results = core.scan_for_header(args.input, scan_alpha=args.scan_alpha, scan_rgb=args.scan_rgb, max_layers=args.scan_layers)
        if results:
            _safe_print(f"Naydeno {len(results)} zagolovkov:")
            for r in results:
                htype = r['header'].get('type', '?')
                _safe_print(f"  Kanal: {r['channel']}, LSB: {r['bits']}, Tip: {htype}, Signatura: {r['header']['signature']}")
        else:
            _safe_print("Zagolovkov ne naydeno")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        main_cli()
    else:
        try:
            import tkinter as tk
            from gui import main
            main()
        except ImportError:
            _safe_print("Ispolzuyte CLI rezhim: python core.py encode input.txt -o output.png")