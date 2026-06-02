import os
import struct
import tempfile
import subprocess
from pathlib import Path

HAS_FFMPEG = False
HAS_PYDUB = False
HAS_IMAGEIO = False

try:
    import imageio.v3 as iio
    import imageio
    HAS_IMAGEIO = True
except ImportError:
    pass

try:
    from pydub import AudioSegment
    HAS_PYDUB = True
except ImportError:
    pass


def check_ffmpeg():
    global HAS_FFMPEG
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        HAS_FFMPEG = True
    except:
        HAS_FFMPEG = False


check_ffmpeg()


AVAILABLE_CODECS = []
if HAS_IMAGEIO:
    AVAILABLE_CODECS.append('GIF')
if HAS_FFMPEG:
    AVAILABLE_CODECS.extend(['MP4', 'MP3'])
if HAS_PYDUB:
    if 'MP3' not in AVAILABLE_CODECS:
        AVAILABLE_CODECS.append('MP3')


class MediaSteganography:
    def __init__(self, debug_callback=None, progress_callback=None):
        self.debug_callback = debug_callback
        self.progress_callback = progress_callback

    def _log(self, msg):
        if self.debug_callback:
            self.debug_callback(msg)

    def _progress(self, cur, total, msg=''):
        if self.progress_callback:
            self.progress_callback(cur, total, msg)

    def encode_gif(self, input_gif_path, data, output_path):
        if not HAS_IMAGEIO:
            raise ImportError("Установите imageio: pip install imageio imageio-ffmpeg")

        reader = imageio.get_reader(input_gif_path)
        meta = reader.get_meta_data()
        fps = meta.get('fps', 10)
        frames = []
        for frame in reader:
            frames.append(frame)
        reader.close()

        if not frames:
            raise ValueError("GIF не содержит кадров")

        data_bytes = data if isinstance(data, bytes) else data.encode('utf-8')
        header = struct.pack('>I', len(data_bytes))
        payload = header + data_bytes
        bits = []
        for byte in payload:
            for b in range(8):
                bits.append((byte >> b) & 1)

        h, w, c = frames[0].shape
        max_bits = len(frames) * h * w
        if len(bits) > max_bits:
            raise ValueError(f"Данные слишком велики: нужно {len(bits)} бит, доступно {max_bits}")

        bit_idx = 0
        for fi in range(len(frames)):
            frame = frames[fi]
            flat = frame.reshape(-1)
            for pi in range(len(flat)):
                if bit_idx >= len(bits):
                    break
                flat[pi] = (flat[pi] & 0xFE) | bits[bit_idx]
                bit_idx += 1
            frames[fi] = frame
            self._progress(fi, len(frames), f"Кадр {fi+1}/{len(frames)}")

        imageio.mimsave(output_path, frames, format='GIF', fps=fps, loop=meta.get('loop', 0))

        return {'success': True, 'output_path': output_path, 'frames': len(frames)}

    def decode_gif(self, input_gif_path, output_path):
        if not HAS_IMAGEIO:
            raise ImportError("Установите imageio: pip install imageio imageio-ffmpeg")

        reader = imageio.get_reader(input_gif_path)
        all_bits = []
        for frame in reader:
            flat = frame.reshape(-1)
            for px in flat:
                all_bits.append(px & 1)
        reader.close()

        header_bits = all_bits[:32]
        data_len = 0
        for i in range(4):
            byte = 0
            for j in range(8):
                if i * 8 + j < len(header_bits):
                    byte |= (header_bits[i * 8 + j] & 1) << j
            data_len = (data_len << 8) | byte

        needed_bits = 32 + data_len * 8
        if needed_bits > len(all_bits):
            raise ValueError(f"Недостаточно данных: нужно {needed_bits} бит, есть {len(all_bits)}")

        data_bytes = bytearray()
        for i in range(data_len):
            byte = 0
            for j in range(8):
                bit_idx = 32 + i * 8 + j
                if bit_idx < len(all_bits):
                    byte |= (all_bits[bit_idx] & 1) << j
            data_bytes.append(byte)

        with open(output_path, 'wb') as f:
            f.write(data_bytes)

        return {'success': True, 'output_path': output_path, 'size': len(data_bytes)}

    def encode_mp4(self, input_video_path, data, output_path, audio_data=None):
        if not HAS_FFMPEG:
            raise ImportError("Установите ffmpeg и ffmpeg-python")

        import imageio

        temp_dir = Path(tempfile.mkdtemp())
        frames_dir = temp_dir / 'frames'
        frames_dir.mkdir()

        reader = imageio.get_reader(input_video_path)
        fps = reader.get_meta_data().get('fps', 30)
        all_frames = []
        for frame in reader:
            all_frames.append(frame)
        reader.close()

        data_bytes = data if isinstance(data, bytes) else data.encode('utf-8')
        header = struct.pack('>I', len(data_bytes))
        payload = header + data_bytes
        bits = []
        for byte in payload:
            for b in range(8):
                bits.append((byte >> b) & 1)

        frame_h, frame_w, frame_c = all_frames[0].shape
        uv_bits_per_frame = (frame_h // 2) * (frame_w // 2) * 2
        total_capacity = len(all_frames) * uv_bits_per_frame

        if len(bits) > total_capacity:
            raise ValueError(f"Данные слишком велики: нужно {len(bits)} бит, доступно {total_capacity}")

        bit_idx = 0
        for fi, frame in enumerate(all_frames):
            if frame_c >= 3:
                yuv = frame.copy()
                uv_flat = yuv[:, :, 1:3].reshape(-1)
                for pi in range(min(len(uv_flat), uv_bits_per_frame)):
                    if bit_idx >= len(bits):
                        break
                    uv_flat[pi] = (uv_flat[pi] & 0xFE) | bits[bit_idx]
                    bit_idx += 1
                yuv[:, :, 1:3] = uv_flat.reshape(frame_h, frame_w, 2)
                all_frames[fi] = yuv

            self._progress(fi, len(all_frames), f"Кадр {fi+1}/{len(all_frames)}")

        import imageio.v3 as i3
        i3.imwrite(str(output_path), all_frames, fps=fps, codec='libx264',
                   pixel_format='yuv420p', output_params=['-preset', 'fast'])

        for f in frames_dir.iterdir():
            f.unlink()
        temp_dir.rmdir()

        result = {'success': True, 'output_path': output_path, 'frames': len(all_frames)}

        if audio_data:
            try:
                import wave
                audio_path = temp_dir / 'audio.wav'
                with wave.open(str(audio_path), 'wb') as wf:
                    wf.setnchannels(2)
                    wf.setsampwidth(2)
                    wf.setframerate(44100)
                    wf.writeframes(audio_data[:44100 * 4])
                result['audio_processed'] = True
            except:
                result['audio_processed'] = False

        return result

    def decode_mp4(self, input_video_path, output_path):
        if not HAS_FFMPEG:
            raise ImportError("Установите ffmpeg и ffmpeg-python")

        import imageio

        reader = imageio.get_reader(input_video_path)
        all_bits = []
        for frame in reader:
            yuv = frame
            uv_flat = yuv[:, :, 1:3].reshape(-1)
            for px in uv_flat:
                all_bits.append(px & 1)
        reader.close()

        header_bits = all_bits[:32]
        data_len = 0
        for i in range(4):
            byte = 0
            for j in range(8):
                if i * 8 + j < len(header_bits):
                    byte |= (header_bits[i * 8 + j] & 1) << j
            data_len = (data_len << 8) | byte

        needed_bits = 32 + data_len * 8
        if needed_bits > len(all_bits):
            raise ValueError(f"Недостаточно данных: нужно {needed_bits} бит, есть {len(all_bits)}")

        data_bytes = bytearray()
        for i in range(data_len):
            byte = 0
            for j in range(8):
                bit_idx = 32 + i * 8 + j
                if bit_idx < len(all_bits):
                    byte |= (all_bits[bit_idx] & 1) << j
            data_bytes.append(byte)

        with open(output_path, 'wb') as f:
            f.write(data_bytes)

        return {'success': True, 'output_path': output_path, 'size': len(data_bytes)}

    def encode_mp3(self, input_mp3_path, data, output_path):
        if not HAS_PYDUB and not HAS_FFMPEG:
            raise ImportError("Установите pydub: pip install pydub")

        from pydub import AudioSegment

        audio = AudioSegment.from_mp3(input_mp3_path)
        raw = audio.raw_data

        data_bytes = data if isinstance(data, bytes) else data.encode('utf-8')
        header = struct.pack('>I', len(data_bytes))
        payload = header + data_bytes
        bits = []
        for byte in payload:
            for b in range(8):
                bits.append((byte >> b) & 1)

        max_bits = len(raw) * 8
        if len(bits) > max_bits:
            raise ValueError(f"Данные слишком велики для MP3-фрейма")

        raw_arr = bytearray(raw)
        bit_idx = 0
        for i in range(min(len(bits), len(raw_arr))):
            raw_arr[i] = (raw_arr[i] & 0xFE) | bits[bit_idx]
            bit_idx += 1

        stego_audio = audio._spawn(raw_arr)
        stego_audio.export(output_path, format='mp3', bitrate='192k')

        return {'success': True, 'output_path': output_path}

    def decode_mp3(self, input_mp3_path, output_path):
        if not HAS_PYDUB:
            raise ImportError("Установите pydub: pip install pydub")

        from pydub import AudioSegment

        audio = AudioSegment.from_mp3(input_mp3_path)
        raw = audio.raw_data

        all_bits = []
        for byte in raw:
            for b in range(8):
                all_bits.append((byte >> b) & 1)

        header_bits = all_bits[:32]
        data_len = 0
        for i in range(4):
            byte = 0
            for j in range(8):
                if i * 8 + j < len(header_bits):
                    byte |= (header_bits[i * 8 + j] & 1) << j
            data_len = (data_len << 8) | byte

        needed_bits = 32 + data_len * 8
        if needed_bits > len(all_bits):
            raise ValueError(f"Недостаточно данных: нужно {needed_bits} бит, есть {len(all_bits)}")

        data_bytes = bytearray()
        for i in range(data_len):
            byte = 0
            for j in range(8):
                bit_idx = 32 + i * 8 + j
                if bit_idx < len(all_bits):
                    byte |= (all_bits[bit_idx] & 1) << j
            data_bytes.append(byte)

        with open(output_path, 'wb') as f:
            f.write(data_bytes)

        return {'success': True, 'output_path': output_path, 'size': len(data_bytes)}
