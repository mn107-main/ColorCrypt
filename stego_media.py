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
    AVAILABLE_CODECS.extend(['MP4', 'MP3', 'Video (FFmpeg)'])
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

    @staticmethod
    def _extract_header_and_data(all_bits):
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

        return bytes(data_bytes)

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
        for fi, frame in enumerate(reader):
            flat = frame.reshape(-1)
            for px in flat:
                all_bits.append(px & 1)
        reader.close()

        data_bytes = self._extract_header_and_data(all_bits)

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

        if not all_frames:
            raise ValueError("Видео не содержит кадров")

        frame_h, frame_w, frame_c = all_frames[0].shape
        # Embed only in G and B channels (indices 1, 2) — less perceptible than R
        channels_per_pixel = 2
        pixels_per_frame = frame_h * frame_w * channels_per_pixel
        total_capacity = len(all_frames) * pixels_per_frame

        if len(bits) > total_capacity:
            raise ValueError(f"Данные слишком велики: нужно {len(bits)} бит, доступно {total_capacity}")

        bit_idx = 0
        for fi, frame in enumerate(all_frames):
            color_flat = frame[:, :, 1:3].reshape(-1)
            for pi in range(min(len(color_flat), pixels_per_frame)):
                if bit_idx >= len(bits):
                    break
                color_flat[pi] = (color_flat[pi] & 0xFE) | bits[bit_idx]
                bit_idx += 1
            all_frames[fi][:, :, 1:3] = color_flat.reshape(frame_h, frame_w, channels_per_pixel)

            self._progress(fi, len(all_frames), f"Кадр {fi+1}/{len(all_frames)}")

        import imageio.v3 as i3
        i3.imwrite(str(output_path), all_frames, fps=fps, codec='libx264',
                   pixel_format='yuv420p', output_params=['-preset', 'fast'])

        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

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
            # Read from G and B channels (indices 1, 2), matching encode_mp4
            color_flat = frame[:, :, 1:3].reshape(-1)
            for px in color_flat:
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

        data_bytes = self._extract_header_and_data(all_bits)

        with open(output_path, 'wb') as f:
            f.write(data_bytes)

        return {'success': True, 'output_path': output_path, 'size': len(data_bytes)}

    def encode_video(self, input_video_path, data, output_path,
                     codec='libx264', bitrate='2M', fps=None):
        if not HAS_FFMPEG:
            raise ImportError("Установите ffmpeg (системный) для этой функции")

        tmp = Path(tempfile.mkdtemp())
        raw_dir = tmp / 'raw'
        raw_dir.mkdir()
        stego_dir = tmp / 'stego'
        stego_dir.mkdir()

        try:
            probe = subprocess.run(
                ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                 '-show_entries', 'stream=r_frame_rate,width,height',
                 '-of', 'csv=p=0', input_video_path],
                capture_output=True, text=True, check=True
            )
            parts = probe.stdout.strip().split(',')
            width, height = int(parts[0]), int(parts[1])
            fps_val = fps or eval(parts[2]) if '/' in parts[2] else float(parts[2])

            subprocess.run(
                ['ffmpeg', '-i', input_video_path, '-q:v', '1',
                 os.path.join(str(raw_dir), 'frame_%05d.png')],
                check=True, capture_output=True
            )

            frame_files = sorted(os.listdir(str(raw_dir)))
            if not frame_files:
                raise ValueError("Видео не содержит кадров")

            data_bytes = data if isinstance(data, bytes) else data.encode('utf-8')
            header = struct.pack('>I', len(data_bytes))
            payload = header + data_bytes
            bits = []
            for byte in payload:
                for b in range(8):
                    bits.append((byte >> b) & 1)

            gb_channels = 2
            total_capacity = len(frame_files) * width * height * gb_channels
            if len(bits) > total_capacity:
                raise ValueError(f"Данные слишком велики: нужно {len(bits)} бит, доступно {total_capacity}")

            bit_idx = 0
            for fi, fn in enumerate(frame_files):
                if bit_idx >= len(bits):
                    break
                from PIL import Image
                import numpy as np
                frame_path = os.path.join(str(raw_dir), fn)
                img = Image.open(frame_path).convert('RGB')
                arr = np.array(img, dtype=np.uint8)
                gb_flat = arr[:, :, 1:3].reshape(-1)
                for pi in range(len(gb_flat)):
                    if bit_idx >= len(bits):
                        break
                    gb_flat[pi] = (gb_flat[pi] & 0xFE) | bits[bit_idx]
                    bit_idx += 1
                arr[:, :, 1:3] = gb_flat.reshape(height, width, 2)
                Image.fromarray(arr).save(os.path.join(str(stego_dir), fn))
                self._progress(fi, len(frame_files), f"Кадр {fi+1}/{len(frame_files)}")

            subprocess.run(
                ['ffmpeg', '-framerate', str(fps_val), '-i',
                 os.path.join(str(stego_dir), 'frame_%05d.png'),
                 '-c:v', codec, '-b:v', bitrate, '-pix_fmt', 'yuv420p',
                 '-y', output_path],
                check=True, capture_output=True
            )

            return {'success': True, 'output_path': output_path, 'frames': len(frame_files)}

        except subprocess.CalledProcessError as e:
            return {'success': False, 'error': f"FFmpeg ошибка: {e.stderr.decode() if e.stderr else str(e)}"}
        except Exception as e:
            return {'success': False, 'error': str(e)}
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

    def decode_video(self, input_video_path, output_path):
        if not HAS_FFMPEG:
            raise ImportError("Установите ffmpeg (системный) для этой функции")

        tmp = Path(tempfile.mkdtemp())
        frames_dir = tmp / 'frames'
        frames_dir.mkdir()

        try:
            subprocess.run(
                ['ffmpeg', '-i', input_video_path, '-q:v', '1',
                 os.path.join(str(frames_dir), 'frame_%05d.png')],
                check=True, capture_output=True
            )

            frame_files = sorted(os.listdir(str(frames_dir)))
            if not frame_files:
                raise ValueError("Видео не содержит кадров")

            from PIL import Image
            import numpy as np
            all_bits = []
            for fi, fn in enumerate(frame_files):
                frame_path = os.path.join(str(frames_dir), fn)
                img = Image.open(frame_path).convert('RGB')
                arr = np.array(img, dtype=np.uint8)
                gb_flat = arr[:, :, 1:3].reshape(-1)
                for px in gb_flat:
                    all_bits.append(px & 1)
                self._progress(fi, len(frame_files), f"Кадр {fi+1}/{len(frame_files)}")

            data_bytes = self._extract_header_and_data(all_bits)

            with open(output_path, 'wb') as f:
                f.write(data_bytes)

            return {'success': True, 'output_path': output_path, 'size': len(data_bytes)}

        except subprocess.CalledProcessError as e:
            return {'success': False, 'error': f"FFmpeg ошибка: {e.stderr.decode() if e.stderr else str(e)}"}
        except Exception as e:
            return {'success': False, 'error': str(e)}
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)
