import numpy as np
from PIL import Image
import struct
import io
import os

HAS_CV2 = False
try:
    import cv2
    HAS_CV2 = True
except ImportError:
    pass

DCT_BLOCK = 8
JPEG_QUALITY = 85

JPEG_DCT_MAGIC = b'\xCC\x0D\xDCT'

def _dct_2d(block):
    return cv2.dct(block.astype(np.float32))

def _idct_2d(block):
    return cv2.idct(block.astype(np.float32))

def _dct_2d_numpy(block):
    M, N = block.shape
    m = np.arange(M)[:, None]
    n = np.arange(N)[None, :]
    u = np.arange(M)[:, None]
    v = np.arange(N)[None, :]
    alpha_u = np.where(u == 0, 1.0 / np.sqrt(M), np.sqrt(2.0 / M))
    alpha_v = np.where(v == 0, 1.0 / np.sqrt(N), np.sqrt(2.0 / N))
    cos_row = np.cos(np.pi * (2 * m + 1) * u / (2 * M))
    cos_col = np.cos(np.pi * (2 * n + 1) * v / (2 * N))
    dct = alpha_u * alpha_v * np.sum(np.sum(block * cos_row[:, :, None, None] * cos_col[None, None, :, :], axis=1), axis=2)
    return dct

def _quantize(dct_block, quality=JPEG_QUALITY):
    scale = 5000 / quality if quality < 50 else 200 - 2 * quality
    Q = np.array([
        [16, 11, 10, 16, 24, 40, 51, 61],
        [12, 12, 14, 19, 26, 58, 60, 55],
        [14, 13, 16, 24, 40, 57, 69, 56],
        [14, 17, 22, 29, 51, 87, 80, 62],
        [18, 22, 37, 56, 68, 109, 103, 77],
        [24, 35, 55, 64, 81, 104, 113, 92],
        [49, 64, 78, 87, 103, 121, 120, 101],
        [72, 92, 95, 98, 112, 100, 103, 99]
    ], dtype=np.float32)
    Q = np.maximum(1, Q * scale / 100)
    return np.round(dct_block / Q)

def _dequantize(q_block, quality=JPEG_QUALITY):
    scale = 5000 / quality if quality < 50 else 200 - 2 * quality
    Q = np.array([
        [16, 11, 10, 16, 24, 40, 51, 61],
        [12, 12, 14, 19, 26, 58, 60, 55],
        [14, 13, 16, 24, 40, 57, 69, 56],
        [14, 17, 22, 29, 51, 87, 80, 62],
        [18, 22, 37, 56, 68, 109, 103, 77],
        [24, 35, 55, 64, 81, 104, 113, 92],
        [49, 64, 78, 87, 103, 121, 120, 101],
        [92, 101, 104, 103, 112, 100, 103, 99]
    ], dtype=np.float32)
    Q = np.maximum(1, Q * scale / 100)
    return q_block * Q

ZIGZAG = np.array([
    0, 1, 8, 16, 9, 2, 3, 10,
    17, 24, 32, 25, 18, 11, 4, 5,
    12, 19, 26, 33, 40, 48, 41, 34,
    27, 20, 13, 6, 7, 14, 21, 28,
    35, 42, 49, 56, 57, 50, 43, 36,
    29, 22, 15, 23, 30, 37, 44, 51,
    58, 59, 52, 45, 38, 31, 39, 46,
    53, 60, 61, 54, 47, 55, 62, 63
])

def _zigzag_flatten(block):
    flat = block.flatten()
    return flat[ZIGZAG]

def _zigzag_unflatten(coeffs, shape=(8, 8)):
    flat = np.zeros(64, dtype=coeffs.dtype)
    zigzag_inv = np.argsort(ZIGZAG)
    flat[zigzag_inv] = coeffs[:64]
    return flat.reshape(shape)

class JPEGDCTSteganography:
    def __init__(self, debug_callback=None, progress_callback=None):
        self.debug_callback = debug_callback
        self.progress_callback = progress_callback

    def _log(self, msg):
        if self.debug_callback:
            self.debug_callback(msg)

    def _progress(self, cur, total, msg=''):
        if self.progress_callback:
            self.progress_callback(cur, total, msg)

    @staticmethod
    def is_jpeg(path):
        ext = os.path.splitext(path)[1].lower()
        return ext in ('.jpg', '.jpeg', '.jfif')

    def _split_blocks(self, image_array):
        h, w = image_array.shape[:2]
        blocks = []
        for y in range(0, h - h % DCT_BLOCK, DCT_BLOCK):
            row_blocks = []
            for x in range(0, w - w % DCT_BLOCK, DCT_BLOCK):
                block = image_array[y:y + DCT_BLOCK, x:x + DCT_BLOCK]
                block = block.astype(np.float32) - 128.0
                if HAS_CV2:
                    dct = _dct_2d(block)
                else:
                    dct = _dct_2d_numpy(block)
                q = _quantize(dct)
                row_blocks.append(q)
            blocks.append(row_blocks)
        return blocks, h, w

    def _reconstruct_from_blocks(self, blocks, h, w, channels):
        canvas = np.zeros((h, w), dtype=np.float32)
        if channels == 1:
            canvas = np.zeros((h, w), dtype=np.float32)
            for by, row in enumerate(blocks):
                for bx, q_block in enumerate(row):
                    dct = _dequantize(q_block)
                    if HAS_CV2:
                        block = _idct_2d(dct) + 128.0
                    else:
                        block = _idct_2d_numpy(dct) + 128.0
                    y, x = by * DCT_BLOCK, bx * DCT_BLOCK
                    canvas[y:y + DCT_BLOCK, x:x + DCT_BLOCK] = block
            return np.clip(canvas, 0, 255).astype(np.uint8)
        else:
            canvases = [np.zeros((h, w), dtype=np.float32) for _ in range(channels)]
            for by, row in enumerate(blocks):
                for bx, ch_blocks in enumerate(row):
                    for c in range(channels):
                        dct = _dequantize(ch_blocks[c])
                        if HAS_CV2:
                            block = _idct_2d(dct) + 128.0
                        else:
                            block = _idct_2d_numpy(dct) + 128.0
                        y, x = by * DCT_BLOCK, bx * DCT_BLOCK
                        canvases[c][y:y + DCT_BLOCK, x:x + DCT_BLOCK] = block
            result = np.stack([np.clip(c, 0, 255).astype(np.uint8) for c in canvases], axis=-1)
            return result

    def encode_dct(self, image_path, data, output_path, use_f5=True):
        img = Image.open(image_path)
        img_mode = img.mode
        if img_mode == 'L':
            channels = 1
            arr = np.array(img, dtype=np.uint8)
        elif img_mode == 'RGBA':
            channels = 3
            arr = np.array(img.convert('RGB'), dtype=np.uint8)
        else:
            channels = 3
            arr = np.array(img.convert('RGB'), dtype=np.uint8)

        h, w = arr.shape[:2]

        data_bytes = data if isinstance(data, bytes) else data.encode('utf-8')
        header = JPEG_DCT_MAGIC + struct.pack('>I', len(data_bytes))
        payload = header + data_bytes

        total_bits_needed = len(payload) * 8

        if channels == 1:
            blocks, _, _ = self._split_blocks(arr)
            num_blocks = sum(len(row) for row in blocks)
            capacity = num_blocks * 63
            if total_bits_needed > capacity:
                raise ValueError(f"JPEG DCT: недостаточно коэффициентов ({capacity} бит, нужно {total_bits_needed})")

            flat_coeffs = []
            block_indices = []
            for by, row in enumerate(blocks):
                for bx, q_block in enumerate(row):
                    zig = _zigzag_flatten(q_block).copy()
                    flat_coeffs.append(zig)
                    block_indices.append((by, bx))

            bit_idx = 0
            bits = np.unpackbits(np.frombuffer(payload, dtype=np.uint8))
            for i, zig in enumerate(flat_coeffs):
                if bit_idx >= len(bits):
                    break
                self._progress(i, len(flat_coeffs), f"DCT block {i+1}/{len(flat_coeffs)}")
                for j in range(1, 64):
                    if bit_idx >= len(bits):
                        break
                    coeff = int(round(zig[j]))
                    if use_f5:
                        if coeff != 0:
                            new_bit = bits[bit_idx]
                            if new_bit == 0:
                                if coeff % 2 == 0:
                                    pass
                                elif abs(coeff) == 1:
                                    zig[j] = 0
                                elif coeff > 0:
                                    zig[j] = coeff - 1
                                else:
                                    zig[j] = coeff + 1
                            else:
                                if coeff % 2 == 1:
                                    pass
                                elif coeff > 0:
                                    zig[j] = coeff + 1
                                elif coeff < 0:
                                    zig[j] = coeff - 1
                                else:
                                    continue
                            bit_idx += 1
                    else:
                        if coeff > 0 and coeff < 63:
                            new_bit = bits[bit_idx]
                            zig[j] = (coeff & 0xFE) | new_bit
                            bit_idx += 1

                by, bx = block_indices[i]
                blocks[by][bx] = _zigzag_unflatten(zig, (8, 8))

            result_arr = self._reconstruct_from_blocks(blocks, h, w, channels)
            result_img = Image.fromarray(result_arr, 'L')
        else:
            ch_blocks_list = []
            num_blocks = 0
            for c in range(channels):
                ch_arr = arr[:, :, c]
                blocks_c, _, _ = self._split_blocks(ch_arr)
                ch_blocks_list.append(blocks_c)
                if c == 0:
                    num_blocks = sum(len(row) for row in blocks_c)

            all_capacity = num_blocks * 63 * channels
            if total_bits_needed > all_capacity:
                raise ValueError(f"JPEG DCT: недостаточно коэффициентов ({all_capacity} бит, нужно {total_bits_needed})")

            bits = np.unpackbits(np.frombuffer(payload, dtype=np.uint8))
            bit_idx = 0

            per_channel_blocks = []
            target_ch = 0
            for by in range(len(ch_blocks_list[0])):
                for bx in range(len(ch_blocks_list[0][by])):
                    block_set = []
                    for c in range(channels):
                        block_set.append(_zigzag_flatten(ch_blocks_list[c][by][bx]).copy())
                    per_channel_blocks.append(block_set)

            for i, block_set in enumerate(per_channel_blocks):
                if bit_idx >= len(bits):
                    break
                self._progress(i, len(per_channel_blocks), f"DCT block {i+1}/{len(per_channel_blocks)}")
                ch_idx = i % channels
                zig = block_set[ch_idx]
                for j in range(1, 64):
                    if bit_idx >= len(bits):
                        break
                    coeff = int(round(zig[j]))
                    if use_f5:
                        if coeff != 0:
                            new_bit = bits[bit_idx]
                            if new_bit == 0:
                                if coeff % 2 == 0:
                                    pass
                                elif abs(coeff) == 1:
                                    zig[j] = 0
                                elif coeff > 0:
                                    zig[j] = coeff - 1
                                else:
                                    zig[j] = coeff + 1
                            else:
                                if coeff % 2 == 1:
                                    pass
                                elif coeff > 0:
                                    zig[j] = coeff + 1
                                elif coeff < 0:
                                    zig[j] = coeff - 1
                                else:
                                    continue
                            bit_idx += 1
                    else:
                        if coeff > 0 and coeff < 63:
                            new_bit = bits[bit_idx]
                            zig[j] = (coeff & 0xFE) | new_bit
                            bit_idx += 1

                block_set[ch_idx] = zig

            for by in range(len(ch_blocks_list[0])):
                for bx in range(len(ch_blocks_list[0][by])):
                    idx = by * len(ch_blocks_list[0][by]) + bx
                    for c in range(channels):
                        ch_blocks_list[c][by][bx] = _zigzag_unflatten(per_channel_blocks[idx][c], (8, 8))

            ch_results = []
            for c in range(channels):
                ch_arr = self._reconstruct_from_blocks(ch_blocks_list[c], h, w, 1)
                ch_results.append(ch_arr)
            result_arr = np.stack(ch_results, axis=-1)
            result_img = Image.fromarray(result_arr, 'RGB')

        result_img.save(output_path, format='JPEG', quality=JPEG_QUALITY, optimize=True)
        return {'success': True, 'output_path': output_path, 'size': len(data_bytes)}

    def decode_dct(self, image_path, output_path):
        img = Image.open(image_path)
        img_mode = img.mode
        if img_mode == 'L':
            channels = 1
            arr = np.array(img, dtype=np.uint8)
        else:
            channels = 3
            arr = np.array(img.convert('RGB'), dtype=np.uint8)

        h, w = arr.shape[:2]

        if channels == 1:
            blocks, _, _ = self._split_blocks(arr)
            flat_coeffs = []
            for by, row in enumerate(blocks):
                for bx, q_block in enumerate(row):
                    zig = _zigzag_flatten(q_block)
                    flat_coeffs.append(zig)
        else:
            ch_blocks_list = []
            for c in range(channels):
                ch_arr = arr[:, :, c]
                blocks_c, _, _ = self._split_blocks(ch_arr)
                ch_blocks_list.append(blocks_c)

            flat_coeffs = []
            for by in range(len(ch_blocks_list[0])):
                for bx in range(len(ch_blocks_list[0][by])):
                    c_idx = 0
                    zig = _zigzag_flatten(ch_blocks_list[c_idx][by][bx]).copy()
                    flat_coeffs.append(zig)

        all_lsbs = np.array([], dtype=np.uint8)
        for i, zig in enumerate(flat_coeffs):
            self._progress(i, len(flat_coeffs), f"Reading DCT block {i+1}/{len(flat_coeffs)}")
            block_lsbs = np.zeros(0, dtype=np.uint8)
            for j in range(1, 64):
                coeff = int(round(zig[j]))
                if coeff != 0:
                    block_lsbs = np.append(block_lsbs, coeff & 1)
            all_lsbs = np.concatenate([all_lsbs, block_lsbs])

        MAX_HDR_BITS = max(len(JPEG_DCT_MAGIC) * 8 + 32, 320)
        hdr_bits = all_lsbs[:MAX_HDR_BITS].astype(np.uint8)
        hdr_bytes = np.packbits(hdr_bits).tobytes()

        sig_pos = hdr_bytes.find(JPEG_DCT_MAGIC)
        if sig_pos < 0:
            return {'success': False, 'error': 'JPEG DCT сигнатура не найдена'}

        offset_bits = sig_pos * 8 + len(JPEG_DCT_MAGIC) * 8
        if offset_bits + 32 > len(all_lsbs):
            return {'success': False, 'error': 'Недостаточно данных для длины'}

        len_bits = all_lsbs[offset_bits:offset_bits + 32].astype(np.uint8)
        data_len = int.from_bytes(np.packbits(len_bits).tobytes(), 'big')

        total_bits_needed = offset_bits + 32 + data_len * 8
        if total_bits_needed > len(all_lsbs):
            return {'success': False, 'error': f'Недостаточно данных: нужно {total_bits_needed} бит, есть {len(all_lsbs)}'}

        data_bits = all_lsbs[offset_bits + 32:offset_bits + 32 + data_len * 8].astype(np.uint8)
        data_bytes = np.packbits(data_bits).tobytes()[:data_len]

        with open(output_path, 'wb') as f:
            f.write(data_bytes)

        return {'success': True, 'output_path': output_path, 'size': len(data_bytes)}
