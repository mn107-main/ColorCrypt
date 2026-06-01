import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, simpledialog
import os
import sys
import secrets
import string
import re
import json
import threading
from functools import partial
import time

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False

from core import ColorCryptCore, MODE_MONO, MODE_RGB, MODE_RGBA, OUTPUT_FORMATS, ENCODE_MODES, CHUNK_SIZES, CURRENT_VERSION

class ColorCryptApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"ColorCrypt — Текст ⇄ Изображение (v{CURRENT_VERSION})")
        self.root.geometry("1200x900")
        self.root.minsize(900, 700)

        self.core = ColorCryptCore(debug_callback=self._debug_log, progress_callback=self._update_progress)

        self.input_file_path = ""
        self.output_file_path = ""
        self.current_operation_thread = None
        self.config_file = "colorcrypt_config.json"
        self.cancel_flag = False

        self.compress_var = tk.BooleanVar(value=False)
        self.compress_level_var = tk.StringVar(value="normal")
        self.channel_mode_var = tk.StringVar(value=MODE_RGB)
        self.integrity_var = tk.BooleanVar(value=True)
        self.debug_var = tk.BooleanVar(value=False)
        self.output_format_var = tk.StringVar(value="PNG")
        self.output_dir_var = tk.StringVar(value="")
        self.encode_mode_var = tk.StringVar(value="base64")
        self.chunk_mode_var = tk.BooleanVar(value=False)
        self.chunk_size_var = tk.StringVar(value="50MB")
        self.preserve_filename_var = tk.BooleanVar(value=True)

        self.encryption_var = tk.BooleanVar(value=False)
        self.password_var = tk.StringVar(value="")
        self.confirm_password_var = tk.StringVar(value="")
        self.hint_var = tk.StringVar(value="")

        self.batch_files = []

        self.load_settings()

        self.create_widgets()

        if HAS_DND:
            self.setup_drag_drop()
            self.status_label.config(text="💡 Перетащите файл сюда")
        else:
            self.status_label.config(text="💡 Выберите файл кнопкой")

        self._update_core_settings()

    def _debug_log(self, message):
        if self.debug_var.get():
            self.debug_log.insert(tk.END, message)
            self.debug_log.see(tk.END)
            self.root.update_idletasks()

    def _update_progress(self, current, total, message=""):
        if hasattr(self, 'progress_var'):
            if total > 0:
                percent = int((current / total) * 100)
            else:
                percent = 0
            self.progress_var.set(percent)
            self.progress_label.config(text=f"{message} ({percent}%)" if message else f"{percent}%")
            self.root.update_idletasks()

    def _update_core_settings(self):
        password = self.password_var.get() if self.encryption_var.get() else None
        self.core.set_settings(
            compress_enabled=self.compress_var.get(),
            compress_level=self.compress_level_var.get(),
            channel_mode=self.channel_mode_var.get(),
            integrity_enabled=self.integrity_var.get(),
            encryption_enabled=self.encryption_var.get(),
            password=password,
            output_format=self.output_format_var.get(),
            make_square=False,
            output_dir=self.output_dir_var.get() if self.output_dir_var.get() else None,
            encode_mode=self.encode_mode_var.get(),
            chunk_mode=self.chunk_mode_var.get(),
            chunk_size=self.chunk_size_var.get(),
            preserve_filename=self.preserve_filename_var.get()
        )

    def save_settings(self):
        settings = {
            'compress': self.compress_var.get(),
            'compress_level': self.compress_level_var.get(),
            'channel_mode': self.channel_mode_var.get(),
            'integrity': self.integrity_var.get(),
            'debug': self.debug_var.get(),
            'output_format': self.output_format_var.get(),
            'output_dir': self.output_dir_var.get(),
            'encode_mode': self.encode_mode_var.get(),
            'chunk_mode': self.chunk_mode_var.get(),
            'chunk_size': self.chunk_size_var.get(),
            'encryption': self.encryption_var.get(),
            'preserve_filename': self.preserve_filename_var.get(),
            'window_geometry': self.root.geometry(),
            'window_state': self.root.state()
        }
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2)
        except:
            pass

    def load_settings(self):
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                self.compress_var.set(settings.get('compress', False))
                self.compress_level_var.set(settings.get('compress_level', 'normal'))
                self.channel_mode_var.set(settings.get('channel_mode', MODE_RGB))
                self.integrity_var.set(settings.get('integrity', True))
                self.debug_var.set(settings.get('debug', False))
                self.output_format_var.set(settings.get('output_format', 'PNG'))
                self.output_dir_var.set(settings.get('output_dir', ''))
                self.encode_mode_var.set(settings.get('encode_mode', 'base64'))
                self.chunk_mode_var.set(settings.get('chunk_mode', False))
                self.chunk_size_var.set(settings.get('chunk_size', '50MB'))
                self.encryption_var.set(settings.get('encryption', False))
                self.preserve_filename_var.set(settings.get('preserve_filename', True))
                if settings.get('window_geometry'):
                    self.root.geometry(settings['window_geometry'])
        except:
            pass

    def check_password_strength(self, password):
        if not password:
            return 0, "❌ Пустой пароль", [], "#ff3300"

        score = 0
        feedback = []

        if len(password) >= 12:
            score += 2
            feedback.append("✓ Длина ≥12 символов")
        elif len(password) >= 8:
            score += 1
            feedback.append("✓ Длина ≥8 символов")
        else:
            feedback.append("✗ Минимум 8 символов")

        if re.search(r'[A-Z]', password):
            score += 1
            feedback.append("✓ Есть заглавные буквы")
        else:
            feedback.append("✗ Добавьте заглавные буквы")

        if re.search(r'[a-z]', password):
            score += 1
            feedback.append("✓ Есть строчные буквы")
        else:
            feedback.append("✗ Добавьте строчные буквы")

        if re.search(r'\d', password):
            score += 1
            feedback.append("✓ Есть цифры")
        else:
            feedback.append("✗ Добавьте цифры")

        if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            score += 1
            feedback.append("✓ Есть спецсимволы")
        else:
            feedback.append("✗ Добавьте спецсимволы")

        if score >= 6:
            strength = "🔒 Очень сильный"
            color = "#00cc00"
        elif score >= 4:
            strength = "🔐 Сильный"
            color = "#66cc00"
        elif score >= 3:
            strength = "⚠️ Средний"
            color = "#ffcc00"
        elif score >= 2:
            strength = "⚠️ Слабый"
            color = "#ff9900"
        else:
            strength = "❌ Очень слабый"
            color = "#ff3300"

        return score, strength, feedback, color

    def on_password_change(self, *args):
        password = self.password_var.get()
        confirm = self.confirm_password_var.get()
        score, strength, feedback, color = self.check_password_strength(password)

        self.strength_label.config(text=strength, foreground=color)

        if password and confirm and password != confirm:
            self.confirm_status_label.config(text="❌ Пароли не совпадают", foreground="#ff3300")
        elif password and confirm:
            self.confirm_status_label.config(text="✅ Пароли совпадают", foreground="#00cc00")
        else:
            self.confirm_status_label.config(text="")

        if self.hint_var.get():
            self.hint_display.config(text=f"💡 Подсказка: {self.hint_var.get()}")
        else:
            self.hint_display.config(text="")

        self._update_core_settings()

    def generate_random_password(self):
        length = 20
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        self.password_var.set(password)
        self.confirm_password_var.set(password)
        self.on_password_change()

        self.root.clipboard_clear()
        self.root.clipboard_append(password)
        self.status_label.config(text="✅ Случайный пароль сгенерирован и скопирован в буфер")

    def select_output_dir(self):
        directory = filedialog.askdirectory(title="Выберите папку для сохранения")
        if directory:
            self.output_dir_var.set(directory)
            if hasattr(self, 'output_dir_label'):
                self.output_dir_label.config(text=directory)

    def add_batch_files(self):
        files = filedialog.askopenfilenames(title="Выберите файлы для обработки")
        if files:
            self.batch_files.extend(files)
            self.update_batch_list()

    def clear_batch_files(self):
        self.batch_files = []
        self.update_batch_list()

    def update_batch_list(self):
        if hasattr(self, 'batch_listbox'):
            self.batch_listbox.delete(0, tk.END)
            for f in self.batch_files:
                self.batch_listbox.insert(tk.END, os.path.basename(f))
        if hasattr(self, 'batch_count_label'):
            self.batch_count_label.config(text=f"Файлов: {len(self.batch_files)}")

    def cancel_operation(self):
        self.core.cancel()
        self.status_label.config(text="⚠️ Отмена операции...")

    def setup_drag_drop(self):
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self.on_file_drop)
        if hasattr(self, 'text_area'):
            self.text_area.drop_target_register(DND_FILES)
            self.text_area.dnd_bind('<<Drop>>', self.on_file_drop)

    def on_file_drop(self, event):
        files = event.data.strip('{}')
        if files:
            if hasattr(self, 'mode_var') and self.mode_var.get() == "encode":
                self.load_file(files.split()[0] if ' ' in files else files)
            else:
                file_list = files.split()
                for f in file_list:
                    if f.lower().endswith(('.png', '.webp', '.bmp')):
                        self.batch_files.append(f)
                self.update_batch_list()

    def create_widgets(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        main_frame = ttk.Frame(notebook)
        notebook.add(main_frame, text="Главная")

        settings_frame = ttk.Frame(notebook)
        notebook.add(settings_frame, text="Настройки")

        security_frame = ttk.Frame(notebook)
        notebook.add(security_frame, text="Безопасность")

        batch_frame = ttk.Frame(notebook)
        notebook.add(batch_frame, text="Пакетная обработка")

        debug_frame = ttk.Frame(notebook)
        notebook.add(debug_frame, text="Отладка")

        mode_frame = ttk.LabelFrame(main_frame, text="Режим работы")
        mode_frame.pack(pady=5, padx=10, fill=tk.X)

        self.mode_var = tk.StringVar(value="encode")
        ttk.Radiobutton(mode_frame, text="📄 Текст → 🖼 Изображение (Кодирование)",
                       variable=self.mode_var, value="encode",
                       command=self.on_mode_change).pack(anchor=tk.W, padx=5, pady=2)
        ttk.Radiobutton(mode_frame, text="🖼 Изображение → 📄 Текст (Декодирование)",
                       variable=self.mode_var, value="decode",
                       command=self.on_mode_change).pack(anchor=tk.W, padx=5, pady=2)

        file_frame = ttk.LabelFrame(main_frame, text="Файл")
        file_frame.pack(pady=5, padx=10, fill=tk.X)

        btn_row = ttk.Frame(file_frame)
        btn_row.pack(pady=5)
        self.btn_select = ttk.Button(btn_row, text="📂 Выбрать файл", command=self.select_file)
        self.btn_select.pack()

        self.file_label = ttk.Label(file_frame, text="Файл не выбран", foreground="gray")
        self.file_label.pack(pady=2)

        text_frame = ttk.LabelFrame(main_frame, text="Содержимое")
        text_frame.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)

        self.text_area = scrolledtext.ScrolledText(text_frame, height=12, font=("Courier", 10), wrap=tk.WORD)
        self.text_area.pack(fill=tk.BOTH, expand=True)

        progress_frame = ttk.LabelFrame(main_frame, text="Прогресс")
        progress_frame.pack(pady=5, padx=10, fill=tk.X)

        self.progress_var = tk.IntVar(value=0)
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var,
                                           maximum=100, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=2)

        self.progress_label = ttk.Label(progress_frame, text="Готов", anchor=tk.CENTER)
        self.progress_label.pack()

        action_frame = ttk.Frame(main_frame)
        action_frame.pack(pady=10)

        self.btn_action = ttk.Button(action_frame, text="▶ Выполнить", command=self.process_file, width=15)
        self.btn_action.pack(side=tk.LEFT, padx=5)

        self.btn_cancel = ttk.Button(action_frame, text="⏹ Отмена", command=self.cancel_operation, width=15)
        self.btn_cancel.pack(side=tk.LEFT, padx=5)

        channel_frame = ttk.LabelFrame(settings_frame, text="Режим записи в изображение")
        channel_frame.pack(pady=5, padx=10, fill=tk.X)

        ttk.Radiobutton(channel_frame, text="1-канальный (только R) — максимальная совместимость",
                        variable=self.channel_mode_var, value=MODE_MONO,
                        command=self._update_core_settings).pack(anchor=tk.W, padx=5, pady=2)
        ttk.Radiobutton(channel_frame, text="3-канальный (RGB) — хорошее сжатие",
                        variable=self.channel_mode_var, value=MODE_RGB,
                        command=self._update_core_settings).pack(anchor=tk.W, padx=5, pady=2)
        ttk.Radiobutton(channel_frame, text="4-канальный (RGBA) — максимальная плотность",
                        variable=self.channel_mode_var, value=MODE_RGBA,
                        command=self._update_core_settings).pack(anchor=tk.W, padx=5, pady=2)

        encode_frame = ttk.LabelFrame(settings_frame, text="Режим кодирования данных")
        encode_frame.pack(pady=5, padx=10, fill=tk.X)

        ttk.Radiobutton(encode_frame, text="Base64 — совместимый режим",
                        variable=self.encode_mode_var, value="base64",
                        command=self._update_core_settings).pack(anchor=tk.W, padx=5, pady=2)

        compress_frame = ttk.LabelFrame(settings_frame, text="Сжатие данных (zlib)")
        compress_frame.pack(pady=5, padx=10, fill=tk.X)

        ttk.Checkbutton(compress_frame, text="Включить сжатие",
                        variable=self.compress_var, command=self._update_core_settings).pack(anchor=tk.W)

        level_frame = ttk.Frame(compress_frame)
        level_frame.pack(pady=5, padx=20, fill=tk.X)
        ttk.Label(level_frame, text="Уровень сжатия:").pack(side=tk.LEFT)
        ttk.Combobox(level_frame, textvariable=self.compress_level_var,
                    values=["none", "min", "normal", "max"], state="readonly", width=10).pack(side=tk.LEFT, padx=5)

        format_frame = ttk.LabelFrame(settings_frame, text="Формат вывода")
        format_frame.pack(pady=5, padx=10, fill=tk.X)

        for fmt in OUTPUT_FORMATS.keys():
            ttk.Radiobutton(format_frame, text=fmt, variable=self.output_format_var,
                           value=fmt, command=self._update_core_settings).pack(anchor=tk.W, padx=5)

        chunk_frame = ttk.LabelFrame(settings_frame, text="Чанковый режим (для больших файлов)")
        chunk_frame.pack(pady=5, padx=10, fill=tk.X)

        ttk.Checkbutton(chunk_frame, text="Разделять на чанки (>2MB)",
                        variable=self.chunk_mode_var, command=self._update_core_settings).pack(anchor=tk.W)

        chunk_size_frame = ttk.Frame(chunk_frame)
        chunk_size_frame.pack(pady=5, padx=20, fill=tk.X)
        ttk.Label(chunk_size_frame, text="Размер чанка:").pack(side=tk.LEFT)
        ttk.Combobox(chunk_size_frame, textvariable=self.chunk_size_var,
                    values=list(CHUNK_SIZES.keys()), state="readonly", width=10).pack(side=tk.LEFT, padx=5)

        opt_frame = ttk.LabelFrame(settings_frame, text="Дополнительные настройки")
        opt_frame.pack(pady=5, padx=10, fill=tk.X)

        ttk.Checkbutton(opt_frame, text="Проверка целостности (SHA-256)",
                        variable=self.integrity_var, command=self._update_core_settings).pack(anchor=tk.W, pady=2)

        ttk.Checkbutton(opt_frame, text="Сохранять оригинальное имя файла",
                        variable=self.preserve_filename_var, command=self._update_core_settings).pack(anchor=tk.W, pady=2)

        output_dir_frame = ttk.LabelFrame(settings_frame, text="Папка для сохранения")
        output_dir_frame.pack(pady=5, padx=10, fill=tk.X)

        dir_row = ttk.Frame(output_dir_frame)
        dir_row.pack(fill=tk.X, pady=5)
        ttk.Button(dir_row, text="📁 Выбрать папку", command=self.select_output_dir).pack(side=tk.LEFT)
        self.output_dir_label = ttk.Label(dir_row, text=self.output_dir_var.get() or "(рядом с исходным)",
                                         foreground="gray")
        self.output_dir_label.pack(side=tk.LEFT, padx=5)

        encrypt_frame = ttk.LabelFrame(security_frame, text="AES-256-GCM Шифрование")
        encrypt_frame.pack(pady=5, padx=10, fill=tk.X)

        ttk.Checkbutton(encrypt_frame, text="Включить шифрование AES-256-GCM",
                        variable=self.encryption_var, command=self._update_core_settings).pack(anchor=tk.W, pady=5)

        password_frame = ttk.Frame(encrypt_frame)
        password_frame.pack(fill=tk.X, pady=5)
        ttk.Label(password_frame, text="Пароль:").pack(side=tk.LEFT)
        self.password_entry = ttk.Entry(password_frame, textvariable=self.password_var, show="*", width=30)
        self.password_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.password_var.trace('w', self.on_password_change)

        confirm_frame = ttk.Frame(encrypt_frame)
        confirm_frame.pack(fill=tk.X, pady=5)
        ttk.Label(confirm_frame, text="Подтверждение:").pack(side=tk.LEFT)
        self.confirm_entry = ttk.Entry(confirm_frame, textvariable=self.confirm_password_var, show="*", width=30)
        self.confirm_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.confirm_password_var.trace('w', self.on_password_change)
        self.confirm_status_label = ttk.Label(confirm_frame, text="", foreground="gray")
        self.confirm_status_label.pack(side=tk.LEFT, padx=5)

        btn_frame = ttk.Frame(encrypt_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="🔒 Сгенерировать пароль",
                   command=self.generate_random_password).pack(side=tk.LEFT, padx=2)

        self.show_password = tk.BooleanVar(value=False)
        ttk.Checkbutton(encrypt_frame, text="Показать пароль",
                        variable=self.show_password,
                        command=self.toggle_password_visibility).pack(anchor=tk.W, pady=2)

        strength_frame = ttk.LabelFrame(encrypt_frame, text="Сложность пароля")
        strength_frame.pack(fill=tk.X, pady=5)
        self.strength_label = ttk.Label(strength_frame, text="❌ Пустой пароль", anchor=tk.CENTER)
        self.strength_label.pack(pady=5)

        hint_frame = ttk.LabelFrame(encrypt_frame, text="Подсказка для пароля")
        hint_frame.pack(fill=tk.X, pady=5)
        self.hint_entry = ttk.Entry(hint_frame, textvariable=self.hint_var, width=50)
        self.hint_entry.pack(fill=tk.X, padx=5, pady=5)
        self.hint_display = ttk.Label(hint_frame, text="", foreground="gray")
        self.hint_display.pack(pady=2)

        info_text = """
        🔐 Информация о шифровании:
        • AES-256-GCM с аутентификацией
        • PBKDF2 (100,000 итераций)
        • Случайная соль (32 байта)
        • Случайный IV/nonce (12 байт)
        • Встроенная проверка целостности
        """
        info_label = ttk.Label(encrypt_frame, text=info_text, justify=tk.LEFT, foreground="gray")
        info_label.pack(anchor=tk.W, pady=5)

        batch_control = ttk.Frame(batch_frame)
        batch_control.pack(pady=5, padx=10, fill=tk.X)
        ttk.Button(batch_control, text="➕ Добавить файлы", command=self.add_batch_files).pack(side=tk.LEFT, padx=2)
        ttk.Button(batch_control, text="🗑 Очистить список", command=self.clear_batch_files).pack(side=tk.LEFT, padx=2)
        self.batch_count_label = ttk.Label(batch_control, text="Файлов: 0")
        self.batch_count_label.pack(side=tk.RIGHT)

        list_frame = ttk.LabelFrame(batch_frame, text="Файлы для обработки")
        list_frame.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.batch_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set)
        self.batch_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.batch_listbox.yview)

        batch_action = ttk.Frame(batch_frame)
        batch_action.pack(pady=10)
        ttk.Button(batch_action, text="▶ Кодировать всё",
                   command=self.batch_encode, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(batch_action, text="◀ Декодировать всё",
                   command=self.batch_decode, width=15).pack(side=tk.LEFT, padx=5)

        debug_opt_frame = ttk.LabelFrame(debug_frame, text="Отладочные опции")
        debug_opt_frame.pack(pady=5, padx=10, fill=tk.X)
        ttk.Checkbutton(debug_opt_frame, text="Режим отладки (подробное логирование)",
                        variable=self.debug_var).pack(anchor=tk.W)
        ttk.Button(debug_opt_frame, text="Очистить лог",
                   command=lambda: self.debug_log.delete(1.0, tk.END)).pack(anchor=tk.W, pady=2)

        self.debug_log = scrolledtext.ScrolledText(debug_frame, height=10, font=("Courier", 9))
        self.debug_log.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)

        self.status_label = ttk.Label(self.root, text="Готов", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        self.save_settings()
        self.root.destroy()

    def toggle_password_visibility(self):
        if self.show_password.get():
            self.password_entry.config(show="")
            self.confirm_entry.config(show="")
        else:
            self.password_entry.config(show="*")
            self.confirm_entry.config(show="*")

    def on_mode_change(self):
        self.text_area.delete(1.0, tk.END)
        self.input_file_path = ""
        self.file_label.config(text="Файл не выбран")

        if self.mode_var.get() == "encode":
            self.btn_select.config(text="📂 Выбрать файл для кодирования")
            self.file_label.config(text="Поддерживаются любые файлы (текстовые, бинарные)")
        else:
            self.btn_select.config(text="📂 Выбрать изображение для декодирования")
            self.file_label.config(text="Поддерживаются PNG, WebP, BMP, созданные ColorCrypt")

    def select_file(self):
        if self.mode_var.get() == "encode":
            ft = [("All files", "*.*"), ("Text files", "*.txt"), ("Binary files", "*.bin")]
            filename = filedialog.askopenfilename(filetypes=ft, title="Выберите файл для кодирования")
        else:
            ft = [("Image files", "*.png *.webp *.bmp"), ("PNG image", "*.png"),
                  ("WebP image", "*.webp"), ("BMP image", "*.bmp")]
            filename = filedialog.askopenfilename(filetypes=ft, title="Выберите изображение для декодирования")

        if filename:
            self.load_file(filename)

    def load_file(self, filename):
        if not os.path.exists(filename):
            messagebox.showerror("Ошибка", "Файл не найден")
            return

        self.input_file_path = filename
        self.file_label.config(text=f"Файл: {os.path.basename(filename)} ({self._format_size(os.path.getsize(filename))})")

        if self.mode_var.get() == "encode":
            self._load_encode_file(filename)
        else:
            self._load_decode_file(filename)

    def _format_size(self, size):
        for unit in ['Б', 'КБ', 'МБ', 'ГБ']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} ТБ"

    def _load_encode_file(self, filename):
        try:
            size = os.path.getsize(filename)

            if size > 1024 * 1024:
                if not messagebox.askyesno("Предупреждение",
                                           f"Файл большой ({self._format_size(size)}). Показать содержимое?"):
                    self.text_area.delete(1.0, tk.END)
                    self.text_area.insert(tk.END, f"[Файл слишком большой для предпросмотра]\nРазмер: {self._format_size(size)}")
                    return
        except:
            pass

        try:
            with open(filename, 'rb') as f:
                raw_data = f.read()

            try:
                text = raw_data.decode('utf-8')
                lines = text.splitlines()
                self.text_area.delete(1.0, tk.END)
                if len(lines) > 100:
                    self.text_area.insert(tk.END, f"[Файл содержит {len(lines)} строк, показаны первые 50]\n\n")
                    self.text_area.insert(tk.END, '\n'.join(lines[:50]))
                    self.text_area.insert(tk.END, f"\n\n... и ещё {len(lines) - 50} строк")
                else:
                    self.text_area.insert(tk.END, text)
            except UnicodeDecodeError:
                self.text_area.delete(1.0, tk.END)
                self.text_area.insert(tk.END, f"[Бинарный файл]\nРазмер: {self._format_size(len(raw_data))}\nSHA-256: {self._calculate_sha256(raw_data)}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось прочитать файл:\n{e}")
            return

        self.status_label.config(text=f"✅ Загружен: {os.path.basename(filename)}")

    def _calculate_sha256(self, data):
        import hashlib
        return hashlib.sha256(data).hexdigest()[:16] + "..."

    def _load_decode_file(self, filename):
        self.text_area.delete(1.0, tk.END)

        try:
            from PIL import Image
            img = Image.open(filename)
            self.text_area.insert(tk.END, f"🖼 Информация об изображении:\n")
            self.text_area.insert(tk.END, f"  Размер: {img.size[0]}x{img.size[1]}\n")
            self.text_area.insert(tk.END, f"  Режим: {img.mode}\n")
            self.text_area.insert(tk.END, f"  Формат: {img.format}\n\n")
            self.text_area.insert(tk.END, f"Нажмите 'Выполнить' для декодирования скрытых данных.")
        except Exception as e:
            self.text_area.insert(tk.END, f"Не удалось прочитать изображение: {e}")

        self.status_label.config(text=f"✅ Загружено: {os.path.basename(filename)}")

    def process_file(self):
        if not self.input_file_path:
            messagebox.showwarning("Предупреждение", "Сначала выберите файл")
            return

        if self.encryption_var.get() and self.mode_var.get() == "encode":
            password = self.password_var.get()
            confirm = self.confirm_password_var.get()
            if not password:
                messagebox.showwarning("Предупреждение", "Введите пароль для шифрования")
                return
            if password != confirm:
                messagebox.showwarning("Предупреждение", "Пароли не совпадают")
                return

        self._update_core_settings()
        self.progress_var.set(0)
        self.btn_action.config(state=tk.DISABLED)
        self.btn_cancel.config(state=tk.NORMAL)

        self.current_operation_thread = threading.Thread(target=self._process_file_thread)
        self.current_operation_thread.daemon = True
        self.current_operation_thread.start()

    def _process_file_thread(self):
        try:
            if self.mode_var.get() == "encode":
                self._encode()
            else:
                self.root.after(0, self._request_password_and_decode)
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Ошибка", str(e)))
        finally:
            self.root.after(0, self._enable_buttons)
            self.root.after(0, lambda: self.progress_var.set(100))

    def _request_password_and_decode(self):
        password = None
        is_encrypted = self.core.check_encryption(self.input_file_path)
        if is_encrypted:
            password = simpledialog.askstring("Введите пароль",
                                              "Файл зашифрован. Введите пароль для расшифровки:",
                                              parent=self.root, show='*')
            if password is None:
                self._enable_buttons()
                return
        threading.Thread(target=self._decode_with_password, args=(password,)).start()

    def _decode_with_password(self, password):
        try:
            output_dir = self.output_dir_var.get() if self.output_dir_var.get() else None
            result = self.core.decode(self.input_file_path, output_dir, password=password)
            self.root.after(0, lambda: self._decode_callback(result))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Ошибка", str(e)))

    def _enable_buttons(self):
        self.btn_action.config(state=tk.NORMAL)
        self.btn_cancel.config(state=tk.NORMAL)

    def _encode(self):
        output_dir = self.output_dir_var.get() if self.output_dir_var.get() else None
        result = self.core.encode(self.input_file_path, output_dir)
        self.root.after(0, lambda: self._encode_callback(result))

    def _encode_callback(self, result):
        if result['success']:
            self.output_file_path = result['output_path']

            self.text_area.delete(1.0, tk.END)
            self.text_area.insert(tk.END, f"✅ Кодирование завершено!\n\n")
            self.text_area.insert(tk.END, f"📁 Сохранено: {result['output_path']}\n")
            self.text_area.insert(tk.END, f"📐 Размер: {result.get('width', '?')}x{result.get('height', '?')}\n")
            self.text_area.insert(tk.END, f"🎨 Формат: {self.output_format_var.get()}\n")
            self.text_area.insert(tk.END, f"💾 Размер файла: {self._format_size(result.get('size', 0))}\n")
            self.text_area.insert(tk.END, f"⏱ Время: {result.get('elapsed', 0):.2f} сек\n")

            if result.get('chunked'):
                self.text_area.insert(tk.END, f"\n📦 Чанковый режим: {result.get('num_chunks', 0)} чанков\n")

            if self.compress_var.get():
                self.text_area.insert(tk.END, f"🗜 Сжатие: {self.compress_level_var.get()}\n")

            if self.encryption_var.get():
                self.text_area.insert(tk.END, f"🔐 Шифрование: AES-256-GCM\n")
                if self.hint_var.get():
                    self.text_area.insert(tk.END, f"💡 Подсказка: {self.hint_var.get()}\n")

            if self.integrity_var.get() and result.get('sha256'):
                self.text_area.insert(tk.END, f"🔑 SHA-256: {result['sha256']}\n")

            self.status_label.config(text=f"✅ Готово: {os.path.basename(result['output_path'])}")

            if self.encryption_var.get() and self.hint_var.get():
                hint_file = os.path.join(os.path.dirname(result['output_path']), "password_hint.txt")
                with open(hint_file, 'w', encoding='utf-8') as f:
                    f.write(f"Файл: {os.path.basename(result['output_path'])}\n")
                    f.write(f"Подсказка: {self.hint_var.get()}\n")
                    f.write(f"Дата: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        else:
            messagebox.showerror("Ошибка", f"Ошибка кодирования:\n{result.get('error', 'Неизвестная ошибка')}")
            self.status_label.config(text="❌ Ошибка кодирования")

    def _decode_callback(self, result):
        if result['success']:
            self.output_file_path = result['output_path']

            self.text_area.delete(1.0, tk.END)
            self.text_area.insert(tk.END, f"✅ Декодирование завершено!\n\n")

            try:
                with open(result['output_path'], 'rb') as f:
                    data = f.read()

                try:
                    text = data.decode('utf-8')
                    lines = text.splitlines()
                    if len(lines) > 50:
                        self.text_area.insert(tk.END, f"[Файл содержит {len(lines)} строк, показаны первые 50]\n\n")
                        self.text_area.insert(tk.END, '\n'.join(lines[:50]))
                        self.text_area.insert(tk.END, f"\n\n... и ещё {len(lines) - 50} строк")
                    else:
                        self.text_area.insert(tk.END, text)
                except UnicodeDecodeError:
                    self.text_area.insert(tk.END, f"[Бинарный файл]\nРазмер: {self._format_size(len(data))}")
            except:
                self.text_area.insert(tk.END, f"Файл сохранён: {result['output_path']}")

            self.text_area.insert(tk.END, f"\n\n📁 Файл сохранён: {result['output_path']}\n")
            self.text_area.insert(tk.END, f"📦 Размер: {self._format_size(result.get('size', 0))}\n")

            if result.get('chunked'):
                self.text_area.insert(tk.END, f"📦 Восстановлено из {result.get('num_chunks', 0)} чанков\n")

            self.status_label.config(text=f"✅ Готово: {os.path.basename(result['output_path'])}")
        else:
            messagebox.showerror("Ошибка", f"Ошибка декодирования:\n{result.get('error', 'Неизвестная ошибка')}")
            self.status_label.config(text="❌ Ошибка декодирования")

    def batch_encode(self):
        if not self.batch_files:
            messagebox.showwarning("Предупреждение", "Сначала добавьте файлы в список")
            return

        if self.encryption_var.get():
            password = self.password_var.get()
            confirm = self.confirm_password_var.get()
            if not password:
                messagebox.showwarning("Предупреждение", "Введите пароль для шифрования")
                return
            if password != confirm:
                messagebox.showwarning("Предупреждение", "Пароли не совпадают")
                return

        self._update_core_settings()

        threading.Thread(target=self._batch_encode_thread).start()

    def _batch_encode_thread(self):
        output_dir = self.output_dir_var.get() if self.output_dir_var.get() else None
        results = self.core.batch_encode(self.batch_files, output_dir)

        success_count = sum(1 for r in results if r.get('success', False))
        self.root.after(0, lambda: messagebox.showinfo("Завершено",
                                                       f"Обработано файлов: {len(results)}\n"
                                                       f"✅ Успешно: {success_count}\n"
                                                       f"❌ Ошибок: {len(results) - success_count}"))

    def batch_decode(self):
        if not self.batch_files:
            messagebox.showwarning("Предупреждение", "Сначала добавьте файлы в список")
            return

        password = None
        any_encrypted = any(self.core.check_encryption(f) for f in self.batch_files)
        if any_encrypted:
            password = simpledialog.askstring("Введите пароль",
                                              "Некоторые файлы зашифрованы. Введите пароль для расшифровки:",
                                              parent=self.root, show='*')
            if password is None:
                return

        self._update_core_settings()

        threading.Thread(target=self._batch_decode_thread, args=(password,)).start()

    def _batch_decode_thread(self, password):
        output_dir = self.output_dir_var.get() if self.output_dir_var.get() else None
        results = self.core.batch_decode(self.batch_files, output_dir, password)

        success_count = sum(1 for r in results if r.get('success', False))
        self.root.after(0, lambda: messagebox.showinfo("Завершено",
                                                       f"Обработано файлов: {len(results)}\n"
                                                       f"✅ Успешно: {success_count}\n"
                                                       f"❌ Ошибок: {len(results) - success_count}"))

def main():
    if HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()

    app = ColorCryptApp(root)
    root.mainloop()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        from core import main_cli
        main_cli()
    else:
        main()