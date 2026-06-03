import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, simpledialog
import os
import sys
import secrets
import string
import re
import json
import threading
import time

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False

from core import ColorCryptCore, MODE_MONO, MODE_RGB, MODE_RGBA, OUTPUT_FORMATS, ENCODE_MODES, CHUNK_SIZES, CURRENT_VERSION
from stego_media import MediaSteganography, AVAILABLE_CODECS

from lang_data import LANG

DARK_COLORS = {
    "bg": "#2b2b2b",
    "fg": "#f0f0f0",
    "select_bg": "#4a4a4a",
    "select_fg": "#ffffff",
    "widget_bg": "#3c3f41",
    "widget_fg": "#e0e0e0",
    "disabled_fg": "#6e6e6e",
    "highlight": "#4a6a9a",
    "entry_bg": "#45474a",
    "entry_fg": "#e0e0e0",
    "button_bg": "#3c3f41",
    "button_fg": "#e0e0e0",
    "frame_bg": "#2b2b2b",
    "label_frame_bg": "#2b2b2b",
    "scroll_bg": "#3c3f41",
    "scroll_trough": "#2b2b2b",
    "progress_bg": "#3c3f41",
    "tabs_bg": "#3c3f41",
    "tab_fg": "#e0e0e0",
    "tab_sel_bg": "#4a6a9a",
    "tab_sel_fg": "#ffffff",
    "notebook_bg": "#2b2b2b",
    "text_bg": "#1e1e1e",
    "text_fg": "#e0e0e0",
    "insert_bg": "#ffffff",
    "status_bg": "#3c3f41",
    "red": "#ff6b68",
    "orange": "#ffa726",
    "green": "#66bb6a",
}

LIGHT_COLORS = {
    "bg": "#f0f0f0",
    "fg": "#000000",
    "select_bg": "#0078d7",
    "select_fg": "#ffffff",
    "widget_bg": "#ffffff",
    "widget_fg": "#000000",
    "disabled_fg": "#a0a0a0",
    "highlight": "#0078d7",
    "entry_bg": "#ffffff",
    "entry_fg": "#000000",
    "button_bg": "#e1e1e1",
    "button_fg": "#000000",
    "frame_bg": "#f0f0f0",
    "label_frame_bg": "#f0f0f0",
    "scroll_bg": "#ffffff",
    "scroll_trough": "#e1e1e1",
    "progress_bg": "#e1e1e1",
    "tabs_bg": "#e1e1e1",
    "tab_fg": "#000000",
    "tab_sel_bg": "#ffffff",
    "tab_sel_fg": "#000000",
    "notebook_bg": "#f0f0f0",
    "text_bg": "#ffffff",
    "text_fg": "#000000",
    "insert_bg": "#000000",
    "status_bg": "#e1e1e1",
    "red": "#d32f2f",
    "orange": "#f57c00",
    "green": "#388e3c",
}


class ColorCryptApp:
    def __init__(self, root):
        self.root = root
        self.core = ColorCryptCore(debug_callback=self._debug_log, progress_callback=self._update_progress)

        self.input_file_path = ""
        self.output_file_path = ""
        self.current_operation_thread = None
        self.config_file = "colorcrypt_config.json"
        self.cancel_flag = False
        self._theme_active = False

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
        self.lsb_bits_var = tk.StringVar(value="0")

        self.encryption_var = tk.BooleanVar(value=False)
        self.password_var = tk.StringVar(value="")
        self.confirm_password_var = tk.StringVar(value="")
        self.hint_var = tk.StringVar(value="")

        self.lang_var = tk.StringVar(value="ru")
        self.dark_mode_var = tk.BooleanVar(value=False)

        self.batch_files = []

        self.iii_container_path = ""
        self.iii_secret_path = ""
        self.iii_output_path = ""

        self.media_input_path = ""
        self.media_output_path = ""
        self.media_data_file = ""
        self.media_codec_var = tk.StringVar(value="GIF")
        self.media_mode_var = tk.StringVar(value="encode")
        self.media_use_alpha_var = tk.BooleanVar(value=True)

        self.lang_var.trace('w', lambda *a: self._on_lang_change())
        self.dark_mode_var.trace('w', lambda *a: self._apply_theme())

        self.load_settings()
        self.create_widgets()
        self._apply_theme()

        if HAS_DND:
            self.setup_drag_drop()
            self.status_label.config(text=self._tr("drop_file"))
        else:
            self.status_label.config(text=self._tr("drop_btn"))

        self._update_core_settings()

    def _tr(self, key, *args):
        lang_dict = LANG.get(self.lang_var.get(), LANG["ru"])
        val = lang_dict.get(key, key)
        if args:
            return val.format(*args)
        return val

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

    def _on_lang_change(self):
        self._refresh_all_texts()
        self._update_core_settings()

    def _refresh_all_texts(self):
        if not hasattr(self, 'notebook'):
            return
        tabs = [
            self._tr("main_tab"), self._tr("settings_tab"), self._tr("security_tab"),
            self._tr("batch_tab"), self._tr("iii_tab"), self._tr("media_tab"),
            self._tr("scanner_tab"), self._tr("debug_tab")
        ]
        for i, tab_text in enumerate(tabs):
            self.notebook.tab(i, text=tab_text)

        self.mode_frame.config(text=self._tr("mode_frame"))
        self.mode_encode_btn.config(text=self._tr("mode_encode"))
        self.mode_decode_btn.config(text=self._tr("mode_decode"))
        self.file_frame.config(text=self._tr("file_frame"))
        self.btn_select.config(text=self._tr("select_file"))
        if not self.input_file_path:
            if self.mode_var.get() == "encode":
                self.file_label.config(text=self._tr("encode_hint"))
            else:
                self.file_label.config(text=self._tr("decode_hint"))
        self.text_frame.config(text=self._tr("content_frame"))
        self.progress_frame.config(text=self._tr("progress_frame"))
        self.progress_label.config(text=self._tr("ready"))
        self.btn_action.config(text=self._tr("execute"))
        self.btn_cancel.config(text=self._tr("cancel"))

        self.channel_frame.config(text=self._tr("channel_frame"))
        self.channel_mono_btn.config(text=self._tr("channel_mono"))
        self.channel_rgb_btn.config(text=self._tr("channel_rgb"))
        self.channel_rgba_btn.config(text=self._tr("channel_rgba"))
        self.encode_frame.config(text=self._tr("encode_frame"))
        self.encode_base64_btn.config(text=self._tr("encode_base64"))
        self.compress_frame.config(text=self._tr("compress_frame"))
        self.compress_chk.config(text=self._tr("compress_enable"))
        self.compress_level_label.config(text=self._tr("compress_level"))
        self.format_frame.config(text=self._tr("format_frame"))
        self.chunk_frame.config(text=self._tr("chunk_frame"))
        self.chunk_chk.config(text=self._tr("chunk_enable"))
        self.chunk_size_label.config(text=self._tr("chunk_size"))
        self.opt_frame.config(text=self._tr("options_frame"))
        self.integrity_chk.config(text=self._tr("integrity"))
        self.preserve_chk.config(text=self._tr("preserve_name"))
        self.lsb_label.config(text=self._tr("lsb_label"))
        self.lsb_hint_label.config(text=self._tr("lsb_hint"))
        self.output_dir_frame.config(text=self._tr("output_dir_frame"))
        self.output_dir_btn.config(text=self._tr("output_dir_btn"))
        if not self.output_dir_var.get():
            self.output_dir_label.config(text=self._tr("output_dir_default"))

        self.encrypt_frame.config(text=self._tr("encrypt_frame"))
        self.encrypt_chk.config(text=self._tr("encrypt_enable"))
        self.password_label.config(text=self._tr("password"))
        self.confirm_label.config(text=self._tr("confirm"))
        self.gen_pw_btn.config(text=self._tr("gen_password"))
        self.show_pw_chk.config(text=self._tr("show_password"))
        self.strength_frame.config(text=self._tr("strength_frame"))
        pw = self.password_var.get()
        if not pw:
            self.strength_label.config(text=self._tr("empty_password"))
        self.hint_frame.config(text=self._tr("hint_frame"))
        self.hint_warn_label.config(text=self._tr("hint_warn"))
        self.encrypt_info_label.config(text=self._tr("encrypt_info"))

        self.batch_add_btn.config(text=self._tr("batch_add"))
        self.batch_clear_btn.config(text=self._tr("batch_clear"))
        self.batch_count_label.config(text=self._tr("batch_count", len(self.batch_files)))
        self.batch_list_frame.config(text=self._tr("batch_list"))
        self.batch_encode_btn.config(text=self._tr("batch_encode_all"))
        self.batch_decode_btn.config(text=self._tr("batch_decode_all"))

        self.iii_container_frame.config(text=self._tr("iii_container_frame"))
        self.iii_container_btn.config(text=self._tr("iii_select_container"))
        if not self.iii_container_path:
            self.iii_container_label.config(text=self._tr("iii_not_selected"))
        self.iii_secret_frame.config(text=self._tr("iii_secret_frame"))
        self.iii_secret_btn.config(text=self._tr("iii_select_secret"))
        if not self.iii_secret_path:
            self.iii_secret_label.config(text=self._tr("iii_not_selected"))
        self.iii_options_frame.config(text=self._tr("iii_options_frame"))
        self.iii_alpha_chk.config(text=self._tr("iii_use_alpha"))
        self.iii_restore_chk.config(text=self._tr("iii_restore"))
        self.iii_output_frame.config(text=self._tr("iii_output_frame"))
        self.iii_output_btn.config(text=self._tr("iii_select_output"))
        if not self.iii_output_path:
            self.iii_output_label.config(text=self._tr("iii_not_specified"))
        self.iii_encode_btn.config(text=self._tr("iii_encode_btn"))
        self.iii_decode_btn.config(text=self._tr("iii_decode_btn"))
        self.iii_result_frame.config(text=self._tr("iii_result_frame"))

        self.media_info_frame.config(text=self._tr("media_codecs"))
        media_status = "\u2705 " + ", ".join(AVAILABLE_CODECS) if AVAILABLE_CODECS else self._tr("media_no_codecs")
        self.media_info_label.config(text=media_status)
        self.media_mode_frame.config(text=self._tr("media_mode_frame"))
        self.media_encode_btn.config(text=self._tr("media_encode_mode"))
        self.media_decode_btn.config(text=self._tr("media_decode_mode"))
        self.media_codec_frame.config(text=self._tr("media_codec_sel"))
        if not AVAILABLE_CODECS:
            self.media_no_codec_label.config(text=self._tr("media_install"))
        self.media_file_frame.config(text=self._tr("media_file_frame"))
        self.media_input_btn.config(text=self._tr("media_select_input"))
        if not self.media_input_path:
            self.media_input_label.config(text=self._tr("iii_not_selected"))
        self.media_data_frame.config(text=self._tr("media_data_frame"))
        self.media_data_btn.config(text=self._tr("media_select_data"))
        if not self.media_data_file:
            self.media_data_label.config(text=self._tr("iii_not_selected"))
        self.media_out_frame.config(text=self._tr("media_output_frame"))
        self.media_output_btn.config(text=self._tr("media_select_output"))
        if not self.media_output_path:
            self.media_output_label.config(text=self._tr("iii_not_specified"))
        self.media_action_btn.config(text=self._tr("media_execute"))

        self.scan_file_frame.config(text=self._tr("scan_file_frame"))
        self.scan_file_btn.config(text=self._tr("scan_select_file"))
        self.scan_opts_frame.config(text=self._tr("scan_opts_frame"))
        self.scan_alpha_chk.config(text=self._tr("scan_alpha"))
        self.scan_rgb_chk.config(text=self._tr("scan_rgb"))
        self.scan_depth_label.config(text=self._tr("scan_depth"))
        self.scan_btn.config(text=self._tr("scan_btn"))
        self.scan_result_frame.config(text=self._tr("scan_result_frame"))

        self.debug_opt_frame.config(text=self._tr("debug_options"))
        self.debug_chk.config(text=self._tr("debug_mode"))
        self.debug_clear_btn.config(text=self._tr("debug_clear"))

        self.lang_label.config(text=self._tr("lang_label"))
        self.theme_chk.config(text=self._tr("theme_label"))

        if not self.input_file_path:
            self.status_label.config(text=self._tr("ready"))

    def _apply_theme(self):
        if not hasattr(self, 'notebook'):
            return
        dark = self.dark_mode_var.get()
        c = DARK_COLORS if dark else LIGHT_COLORS
        style = ttk.Style()
        try:
            theme = "clam"
            style.theme_use(theme)
        except:
            pass

        style.configure("TNotebook", background=c["notebook_bg"], borderwidth=0)
        style.configure("TNotebook.Tab", background=c["tabs_bg"], foreground=c["tab_fg"],
                        padding=[10, 3], borderwidth=1)
        style.map("TNotebook.Tab", background=[("selected", c["tab_sel_bg"])],
                  foreground=[("selected", c["tab_sel_fg"])])

        style.configure("TFrame", background=c["frame_bg"])
        style.configure("TLabelframe", background=c["label_frame_bg"], foreground=c["fg"])
        style.configure("TLabelframe.Label", background=c["label_frame_bg"], foreground=c["fg"])

        style.configure("TLabel", background=c["bg"], foreground=c["fg"])
        style.configure("TButton", background=c["button_bg"], foreground=c["button_fg"],
                        bordercolor=c["highlight"], focuscolor=c["highlight"])
        style.map("TButton", background=[("active", c["highlight"])],
                  foreground=[("active", c["button_fg"])])

        style.configure("TCheckbutton", background=c["bg"], foreground=c["fg"])
        style.map("TCheckbutton", background=[("active", c["bg"])])

        style.configure("TRadiobutton", background=c["bg"], foreground=c["fg"])
        style.map("TRadiobutton", background=[("active", c["bg"])])

        style.configure("TCombobox", fieldbackground=c["entry_bg"], background=c["widget_bg"],
                        foreground=c["entry_fg"], arrowcolor=c["fg"])
        style.map("TCombobox", fieldbackground=[("readonly", c["entry_bg"])],
                  foreground=[("readonly", c["entry_fg"])])

        style.configure("TSpinbox", fieldbackground=c["entry_bg"], background=c["widget_bg"],
                        foreground=c["entry_fg"])

        style.configure("Horizontal.TProgressbar", background=c["highlight"],
                        troughcolor=c["progress_bg"], bordercolor=c["progress_bg"],
                        lightcolor=c["highlight"], darkcolor=c["highlight"])

        style.configure("TEntry", fieldbackground=c["entry_bg"], foreground=c["entry_fg"])

        self.root.configure(bg=c["bg"])

        for widget in [self.root, self.status_label]:
            try:
                widget.configure(bg=c["status_bg"])
            except:
                pass

        text_widgets = []
        if hasattr(self, 'text_area'):
            text_widgets.append(self.text_area)
        if hasattr(self, 'debug_log'):
            text_widgets.append(self.debug_log)
        if hasattr(self, 'iii_result_text'):
            text_widgets.append(self.iii_result_text)
        if hasattr(self, 'scan_result_text'):
            text_widgets.append(self.scan_result_text)
        if hasattr(self, 'batch_listbox'):
            text_widgets.append(self.batch_listbox)

        for tw in text_widgets:
            try:
                tw.configure(bg=c["text_bg"], fg=c["text_fg"],
                             insertbackground=c["insert_bg"],
                             selectbackground=c["select_bg"],
                             selectforeground=c["select_fg"])
            except:
                pass

        if hasattr(self, 'status_label'):
            self.status_label.configure(background=c["status_bg"], foreground=c["fg"])

        self._theme_active = True
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
            preserve_filename=self.preserve_filename_var.get(),
            lsb_bits=int(self.lsb_bits_var.get())
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
            'lsb_bits': int(self.lsb_bits_var.get()),
            'lang': self.lang_var.get(),
            'dark_mode': self.dark_mode_var.get(),
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
                self.lsb_bits_var.set(str(settings.get('lsb_bits', 0)))
                self.lang_var.set(settings.get('lang', 'ru'))
                self.dark_mode_var.set(settings.get('dark_mode', False))
                if settings.get('window_geometry'):
                    self.root.geometry(settings['window_geometry'])
        except:
            pass

    def check_password_strength(self, password):
        if not password:
            return 0, self._tr("password_empty"), [], "#ff3300"

        score = 0
        feedback = []

        if len(password) >= 12:
            score += 2
            feedback.append(self._tr("pass_len_ge12"))
        elif len(password) >= 8:
            score += 1
            feedback.append(self._tr("pass_len_ge8"))
        else:
            feedback.append(self._tr("pass_len_min8"))

        if re.search(r'[A-Z]', password):
            score += 1
            feedback.append(self._tr("pass_upper"))
        else:
            feedback.append(self._tr("pass_no_upper"))

        if re.search(r'[a-z]', password):
            score += 1
            feedback.append(self._tr("pass_lower"))
        else:
            feedback.append(self._tr("pass_no_lower"))

        if re.search(r'\d', password):
            score += 1
            feedback.append(self._tr("pass_digit"))
        else:
            feedback.append(self._tr("pass_no_digit"))

        if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            score += 1
            feedback.append(self._tr("pass_special"))
        else:
            feedback.append(self._tr("pass_no_special"))

        if score >= 6:
            strength = self._tr("password_very_strong")
            color = "#00cc00"
        elif score >= 4:
            strength = self._tr("password_strong")
            color = "#66cc00"
        elif score >= 3:
            strength = self._tr("password_medium")
            color = "#ffcc00"
        elif score >= 2:
            strength = self._tr("password_weak")
            color = "#ff9900"
        else:
            strength = self._tr("password_very_weak")
            color = "#ff3300"

        return score, strength, feedback, color

    def on_password_change(self, *args):
        password = self.password_var.get()
        confirm = self.confirm_password_var.get()
        score, strength, feedback, color = self.check_password_strength(password)

        self.strength_label.config(text=strength, foreground=color)

        if password and confirm and password != confirm:
            self.confirm_status_label.config(text=self._tr("password_no_match"), foreground="#ff3300")
        elif password and confirm:
            self.confirm_status_label.config(text=self._tr("password_match"), foreground="#00cc00")
        else:
            self.confirm_status_label.config(text="")

        if self.hint_var.get():
            self.hint_display.config(text=self._tr("hint_display", self.hint_var.get()))
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
        self.status_label.config(text=self._tr("pass_generated"))

    def select_output_dir(self):
        directory = filedialog.askdirectory(title=self._tr("select_output_dir"))
        if directory:
            self.output_dir_var.set(directory)
            if hasattr(self, 'output_dir_label'):
                self.output_dir_label.config(text=directory)

    def add_batch_files(self):
        files = filedialog.askopenfilenames(title=self._tr("select_encode"))
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
            self.batch_count_label.config(text=self._tr("batch_count", len(self.batch_files)))

    def cancel_operation(self):
        self.core.cancel()
        self.status_label.config(text=self._tr("cancel_operation"))

    def setup_drag_drop(self):
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self.on_file_drop)
        if hasattr(self, 'text_area'):
            self.text_area.drop_target_register(DND_FILES)
            self.text_area.dnd_bind('<<Drop>>', self.on_file_drop)

    def on_file_drop(self, event):
        files = event.data.strip('{}')
        if files:
            file_list = files.split()
            self.load_file(file_list[0])

    def create_widgets(self):
        self.root.title(self._tr("app_title", CURRENT_VERSION))
        self.root.geometry("1200x900")
        self.root.minsize(900, 700)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        main_frame = ttk.Frame(self.notebook)
        self.notebook.add(main_frame, text=self._tr("main_tab"))

        settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(settings_frame, text=self._tr("settings_tab"))

        security_frame = ttk.Frame(self.notebook)
        self.notebook.add(security_frame, text=self._tr("security_tab"))

        batch_frame = ttk.Frame(self.notebook)
        self.notebook.add(batch_frame, text=self._tr("batch_tab"))

        iii_frame = ttk.Frame(self.notebook)
        self.notebook.add(iii_frame, text=self._tr("iii_tab"))

        media_frame = ttk.Frame(self.notebook)
        self.notebook.add(media_frame, text=self._tr("media_tab"))

        scan_frame = ttk.Frame(self.notebook)
        self.notebook.add(scan_frame, text=self._tr("scanner_tab"))

        debug_frame = ttk.Frame(self.notebook)
        self.notebook.add(debug_frame, text=self._tr("debug_tab"))

        self.mode_frame = ttk.LabelFrame(main_frame, text=self._tr("mode_frame"))
        self.mode_frame.pack(pady=5, padx=10, fill=tk.X)

        self.mode_var = tk.StringVar(value="encode")
        self.mode_encode_btn = ttk.Radiobutton(self.mode_frame, text=self._tr("mode_encode"),
                                                variable=self.mode_var, value="encode",
                                                command=self.on_mode_change)
        self.mode_encode_btn.pack(anchor=tk.W, padx=5, pady=2)
        self.mode_decode_btn = ttk.Radiobutton(self.mode_frame, text=self._tr("mode_decode"),
                                               variable=self.mode_var, value="decode",
                                               command=self.on_mode_change)
        self.mode_decode_btn.pack(anchor=tk.W, padx=5, pady=2)

        self.file_frame = ttk.LabelFrame(main_frame, text=self._tr("file_frame"))
        self.file_frame.pack(pady=5, padx=10, fill=tk.X)

        btn_row = ttk.Frame(self.file_frame)
        btn_row.pack(pady=5)
        self.btn_select = ttk.Button(btn_row, text=self._tr("select_file"), command=self.select_file)
        self.btn_select.pack()

        self.file_label = ttk.Label(self.file_frame, text=self._tr("no_file"), foreground="gray")
        self.file_label.pack(pady=2)

        self.text_frame = ttk.LabelFrame(main_frame, text=self._tr("content_frame"))
        self.text_frame.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)

        self.text_area = scrolledtext.ScrolledText(self.text_frame, height=12, font=("Courier", 10), wrap=tk.WORD)
        self.text_area.pack(fill=tk.BOTH, expand=True)

        self.progress_frame = ttk.LabelFrame(main_frame, text=self._tr("progress_frame"))
        self.progress_frame.pack(pady=5, padx=10, fill=tk.X)

        self.progress_var = tk.IntVar(value=0)
        self.progress_bar = ttk.Progressbar(self.progress_frame, variable=self.progress_var,
                                            maximum=100, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=2)

        self.progress_label = ttk.Label(self.progress_frame, text=self._tr("ready"), anchor=tk.CENTER)
        self.progress_label.pack()

        action_frame = ttk.Frame(main_frame)
        action_frame.pack(pady=10)

        self.btn_action = ttk.Button(action_frame, text=self._tr("execute"), command=self.process_file, width=15)
        self.btn_action.pack(side=tk.LEFT, padx=5)

        self.btn_cancel = ttk.Button(action_frame, text=self._tr("cancel"), command=self.cancel_operation, width=15)
        self.btn_cancel.pack(side=tk.LEFT, padx=5)

        self.channel_frame = ttk.LabelFrame(settings_frame, text=self._tr("channel_frame"))
        self.channel_frame.pack(pady=5, padx=10, fill=tk.X)

        self.channel_mono_btn = ttk.Radiobutton(self.channel_frame, text=self._tr("channel_mono"),
                                                 variable=self.channel_mode_var, value=MODE_MONO,
                                                 command=self._update_core_settings)
        self.channel_mono_btn.pack(anchor=tk.W, padx=5, pady=2)
        self.channel_rgb_btn = ttk.Radiobutton(self.channel_frame, text=self._tr("channel_rgb"),
                                               variable=self.channel_mode_var, value=MODE_RGB,
                                               command=self._update_core_settings)
        self.channel_rgb_btn.pack(anchor=tk.W, padx=5, pady=2)
        self.channel_rgba_btn = ttk.Radiobutton(self.channel_frame, text=self._tr("channel_rgba"),
                                                variable=self.channel_mode_var, value=MODE_RGBA,
                                                command=self._update_core_settings)
        self.channel_rgba_btn.pack(anchor=tk.W, padx=5, pady=2)

        self.encode_frame = ttk.LabelFrame(settings_frame, text=self._tr("encode_frame"))
        self.encode_frame.pack(pady=5, padx=10, fill=tk.X)

        self.encode_base64_btn = ttk.Radiobutton(self.encode_frame, text=self._tr("encode_base64"),
                                                 variable=self.encode_mode_var, value="base64",
                                                 command=self._update_core_settings)
        self.encode_base64_btn.pack(anchor=tk.W, padx=5, pady=2)

        self.compress_frame = ttk.LabelFrame(settings_frame, text=self._tr("compress_frame"))
        self.compress_frame.pack(pady=5, padx=10, fill=tk.X)

        self.compress_chk = ttk.Checkbutton(self.compress_frame, text=self._tr("compress_enable"),
                                            variable=self.compress_var, command=self._update_core_settings)
        self.compress_chk.pack(anchor=tk.W)

        level_f = ttk.Frame(self.compress_frame)
        level_f.pack(pady=5, padx=20, fill=tk.X)
        self.compress_level_label = ttk.Label(level_f, text=self._tr("compress_level"))
        self.compress_level_label.pack(side=tk.LEFT)
        ttk.Combobox(level_f, textvariable=self.compress_level_var,
                     values=["none", "min", "normal", "max"], state="readonly", width=10).pack(side=tk.LEFT, padx=5)

        self.format_frame = ttk.LabelFrame(settings_frame, text=self._tr("format_frame"))
        self.format_frame.pack(pady=5, padx=10, fill=tk.X)

        for fmt in OUTPUT_FORMATS.keys():
            ttk.Radiobutton(self.format_frame, text=fmt, variable=self.output_format_var,
                            value=fmt, command=self._update_core_settings).pack(anchor=tk.W, padx=5)

        self.chunk_frame = ttk.LabelFrame(settings_frame, text=self._tr("chunk_frame"))
        self.chunk_frame.pack(pady=5, padx=10, fill=tk.X)

        self.chunk_chk = ttk.Checkbutton(self.chunk_frame, text=self._tr("chunk_enable"),
                                         variable=self.chunk_mode_var, command=self._update_core_settings)
        self.chunk_chk.pack(anchor=tk.W)

        cs_f = ttk.Frame(self.chunk_frame)
        cs_f.pack(pady=5, padx=20, fill=tk.X)
        self.chunk_size_label = ttk.Label(cs_f, text=self._tr("chunk_size"))
        self.chunk_size_label.pack(side=tk.LEFT)
        ttk.Combobox(cs_f, textvariable=self.chunk_size_var,
                     values=list(CHUNK_SIZES.keys()), state="readonly", width=10).pack(side=tk.LEFT, padx=5)

        self.opt_frame = ttk.LabelFrame(settings_frame, text=self._tr("options_frame"))
        self.opt_frame.pack(pady=5, padx=10, fill=tk.X)

        self.integrity_chk = ttk.Checkbutton(self.opt_frame, text=self._tr("integrity"),
                                             variable=self.integrity_var, command=self._update_core_settings)
        self.integrity_chk.pack(anchor=tk.W, pady=2)

        self.preserve_chk = ttk.Checkbutton(self.opt_frame, text=self._tr("preserve_name"),
                                            variable=self.preserve_filename_var, command=self._update_core_settings)
        self.preserve_chk.pack(anchor=tk.W, pady=2)

        lsb_f = ttk.Frame(self.opt_frame)
        lsb_f.pack(fill=tk.X, padx=5, pady=2)
        self.lsb_label = ttk.Label(lsb_f, text=self._tr("lsb_label"))
        self.lsb_label.pack(side=tk.LEFT)
        ttk.Combobox(lsb_f, textvariable=self.lsb_bits_var,
                     values=[0, 1, 2, 3, 4], state="readonly", width=5).pack(side=tk.LEFT, padx=5)
        self.lsb_hint_label = ttk.Label(lsb_f, text=self._tr("lsb_hint"), foreground="gray")
        self.lsb_hint_label.pack(side=tk.LEFT, padx=2)

        self.output_dir_frame = ttk.LabelFrame(settings_frame, text=self._tr("output_dir_frame"))
        self.output_dir_frame.pack(pady=5, padx=10, fill=tk.X)

        dir_row = ttk.Frame(self.output_dir_frame)
        dir_row.pack(fill=tk.X, pady=5)
        self.output_dir_btn = ttk.Button(dir_row, text=self._tr("output_dir_btn"), command=self.select_output_dir)
        self.output_dir_btn.pack(side=tk.LEFT)
        self.output_dir_label = ttk.Label(dir_row, text=self.output_dir_var.get() or self._tr("output_dir_default"),
                                          foreground="gray")
        self.output_dir_label.pack(side=tk.LEFT, padx=5)

        ui_frame = ttk.LabelFrame(settings_frame, text="UI")
        ui_frame.pack(pady=5, padx=10, fill=tk.X)
        ui_lang_row = ttk.Frame(ui_frame)
        ui_lang_row.pack(fill=tk.X, padx=5, pady=5)
        self.lang_label = ttk.Label(ui_lang_row, text=self._tr("lang_label"))
        self.lang_label.pack(side=tk.LEFT)
        lang_combo = ttk.Combobox(ui_lang_row, textvariable=self.lang_var,
                                  values=["ru", "en"], state="readonly", width=5)
        lang_combo.pack(side=tk.LEFT, padx=5)
        self.theme_chk = ttk.Checkbutton(ui_frame, text=self._tr("theme_label"), variable=self.dark_mode_var)
        self.theme_chk.pack(anchor=tk.W, padx=5, pady=5)

        self.encrypt_frame = ttk.LabelFrame(security_frame, text=self._tr("encrypt_frame"))
        self.encrypt_frame.pack(pady=5, padx=10, fill=tk.X)

        self.encrypt_chk = ttk.Checkbutton(self.encrypt_frame, text=self._tr("encrypt_enable"),
                                           variable=self.encryption_var, command=self._update_core_settings)
        self.encrypt_chk.pack(anchor=tk.W, pady=5)

        pw_row = ttk.Frame(self.encrypt_frame)
        pw_row.pack(fill=tk.X, pady=5)
        self.password_label = ttk.Label(pw_row, text=self._tr("password"))
        self.password_label.pack(side=tk.LEFT)
        self.password_entry = ttk.Entry(pw_row, textvariable=self.password_var, show="*", width=30)
        self.password_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.password_var.trace('w', self.on_password_change)

        cf_row = ttk.Frame(self.encrypt_frame)
        cf_row.pack(fill=tk.X, pady=5)
        self.confirm_label = ttk.Label(cf_row, text=self._tr("confirm"))
        self.confirm_label.pack(side=tk.LEFT)
        self.confirm_entry = ttk.Entry(cf_row, textvariable=self.confirm_password_var, show="*", width=30)
        self.confirm_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.confirm_password_var.trace('w', self.on_password_change)
        self.confirm_status_label = ttk.Label(cf_row, text="", foreground="gray")
        self.confirm_status_label.pack(side=tk.LEFT, padx=5)

        gen_row = ttk.Frame(self.encrypt_frame)
        gen_row.pack(fill=tk.X, pady=5)
        self.gen_pw_btn = ttk.Button(gen_row, text=self._tr("gen_password"), command=self.generate_random_password)
        self.gen_pw_btn.pack(side=tk.LEFT, padx=2)

        self.show_password = tk.BooleanVar(value=False)
        self.show_pw_chk = ttk.Checkbutton(self.encrypt_frame, text=self._tr("show_password"),
                                           variable=self.show_password,
                                           command=self.toggle_password_visibility)
        self.show_pw_chk.pack(anchor=tk.W, pady=2)

        self.strength_frame = ttk.LabelFrame(self.encrypt_frame, text=self._tr("strength_frame"))
        self.strength_frame.pack(fill=tk.X, pady=5)
        self.strength_label = ttk.Label(self.strength_frame, text=self._tr("empty_password"), anchor=tk.CENTER)
        self.strength_label.pack(pady=5)

        self.hint_frame = ttk.LabelFrame(self.encrypt_frame, text=self._tr("hint_frame"))
        self.hint_frame.pack(fill=tk.X, pady=5)
        self.hint_warn_label = ttk.Label(self.hint_frame, text=self._tr("hint_warn"),
                                         foreground="#ff6600", wraplength=500)
        self.hint_warn_label.pack(padx=5, pady=2)
        self.hint_entry = ttk.Entry(self.hint_frame, textvariable=self.hint_var, width=50)
        self.hint_entry.pack(fill=tk.X, padx=5, pady=5)
        self.hint_display = ttk.Label(self.hint_frame, text="", foreground="gray")
        self.hint_display.pack(pady=2)

        self.encrypt_info_label = ttk.Label(self.encrypt_frame, text=self._tr("encrypt_info"),
                                            justify=tk.LEFT, foreground="gray")
        self.encrypt_info_label.pack(anchor=tk.W, pady=5)

        batch_control = ttk.Frame(batch_frame)
        batch_control.pack(pady=5, padx=10, fill=tk.X)
        self.batch_add_btn = ttk.Button(batch_control, text=self._tr("batch_add"), command=self.add_batch_files)
        self.batch_add_btn.pack(side=tk.LEFT, padx=2)
        self.batch_clear_btn = ttk.Button(batch_control, text=self._tr("batch_clear"), command=self.clear_batch_files)
        self.batch_clear_btn.pack(side=tk.LEFT, padx=2)
        self.batch_count_label = ttk.Label(batch_control, text=self._tr("batch_count", 0))
        self.batch_count_label.pack(side=tk.RIGHT)

        self.batch_list_frame = ttk.LabelFrame(batch_frame, text=self._tr("batch_list"))
        self.batch_list_frame.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(self.batch_list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.batch_listbox = tk.Listbox(self.batch_list_frame, yscrollcommand=scrollbar.set)
        self.batch_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.batch_listbox.yview)

        batch_action = ttk.Frame(batch_frame)
        batch_action.pack(pady=10)
        self.batch_encode_btn = ttk.Button(batch_action, text=self._tr("batch_encode_all"),
                                           command=self.batch_encode, width=15)
        self.batch_encode_btn.pack(side=tk.LEFT, padx=5)
        self.batch_decode_btn = ttk.Button(batch_action, text=self._tr("batch_decode_all"),
                                           command=self.batch_decode, width=15)
        self.batch_decode_btn.pack(side=tk.LEFT, padx=5)

        self.iii_container_frame = ttk.LabelFrame(iii_frame, text=self._tr("iii_container_frame"))
        self.iii_container_frame.pack(pady=5, padx=10, fill=tk.X)
        self.iii_container_btn = ttk.Button(self.iii_container_frame, text=self._tr("iii_select_container"),
                                            command=self._iii_select_container)
        self.iii_container_btn.pack(pady=5)
        self.iii_container_label = ttk.Label(self.iii_container_frame, text=self._tr("iii_not_selected"), foreground="gray")
        self.iii_container_label.pack(pady=2)

        self.iii_secret_frame = ttk.LabelFrame(iii_frame, text=self._tr("iii_secret_frame"))
        self.iii_secret_frame.pack(pady=5, padx=10, fill=tk.X)
        self.iii_secret_btn = ttk.Button(self.iii_secret_frame, text=self._tr("iii_select_secret"),
                                         command=self._iii_select_secret)
        self.iii_secret_btn.pack(pady=5)
        self.iii_secret_label = ttk.Label(self.iii_secret_frame, text=self._tr("iii_not_selected"), foreground="gray")
        self.iii_secret_label.pack(pady=2)

        self.iii_options_frame = ttk.LabelFrame(iii_frame, text=self._tr("iii_options_frame"))
        self.iii_options_frame.pack(pady=5, padx=10, fill=tk.X)
        self.iii_use_alpha_var = tk.BooleanVar(value=True)
        self.iii_alpha_chk = ttk.Checkbutton(self.iii_options_frame, text=self._tr("iii_use_alpha"),
                                             variable=self.iii_use_alpha_var)
        self.iii_alpha_chk.pack(anchor=tk.W, padx=5, pady=2)
        self.iii_restore_var = tk.BooleanVar(value=False)
        self.iii_restore_chk = ttk.Checkbutton(self.iii_options_frame, text=self._tr("iii_restore"),
                                               variable=self.iii_restore_var)
        self.iii_restore_chk.pack(anchor=tk.W, padx=5, pady=2)

        self.iii_output_frame = ttk.LabelFrame(iii_frame, text=self._tr("iii_output_frame"))
        self.iii_output_frame.pack(pady=5, padx=10, fill=tk.X)
        self.iii_output_btn = ttk.Button(self.iii_output_frame, text=self._tr("iii_select_output"),
                                         command=self._iii_select_output)
        self.iii_output_btn.pack(pady=5)
        self.iii_output_label = ttk.Label(self.iii_output_frame, text=self._tr("iii_not_specified"), foreground="gray")
        self.iii_output_label.pack(pady=2)

        iii_action_frame = ttk.Frame(iii_frame)
        iii_action_frame.pack(pady=10)
        self.iii_encode_btn = ttk.Button(iii_action_frame, text=self._tr("iii_encode_btn"),
                                         command=self._iii_encode, width=35)
        self.iii_encode_btn.pack(pady=2)
        self.iii_decode_btn = ttk.Button(iii_action_frame, text=self._tr("iii_decode_btn"),
                                         command=self._iii_decode, width=35)
        self.iii_decode_btn.pack(pady=2)

        self.iii_status_label = ttk.Label(iii_frame, text=self._tr("ready"), foreground="gray")
        self.iii_status_label.pack(pady=5)

        self.iii_result_frame = ttk.LabelFrame(iii_frame, text=self._tr("iii_result_frame"))
        self.iii_result_frame.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)
        self.iii_result_text = scrolledtext.ScrolledText(self.iii_result_frame, height=8, font=("Courier", 9))
        self.iii_result_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.media_info_frame = ttk.LabelFrame(media_frame, text=self._tr("media_codecs"))
        self.media_info_frame.pack(pady=5, padx=10, fill=tk.X)
        media_status = "\u2705 " + ", ".join(AVAILABLE_CODECS) if AVAILABLE_CODECS else self._tr("media_no_codecs")
        self.media_info_label = ttk.Label(self.media_info_frame, text=media_status)
        self.media_info_label.pack(pady=5)

        self.media_mode_frame = ttk.LabelFrame(media_frame, text=self._tr("media_mode_frame"))
        self.media_mode_frame.pack(pady=5, padx=10, fill=tk.X)
        self.media_encode_btn = ttk.Radiobutton(self.media_mode_frame, text=self._tr("media_encode_mode"),
                                                variable=self.media_mode_var, value="encode")
        self.media_encode_btn.pack(anchor=tk.W, padx=5, pady=2)
        self.media_decode_btn = ttk.Radiobutton(self.media_mode_frame, text=self._tr("media_decode_mode"),
                                                variable=self.media_mode_var, value="decode")
        self.media_decode_btn.pack(anchor=tk.W, padx=5, pady=2)

        self.media_codec_frame = ttk.LabelFrame(media_frame, text=self._tr("media_codec_sel"))
        self.media_codec_frame.pack(pady=5, padx=10, fill=tk.X)
        if AVAILABLE_CODECS:
            ttk.Combobox(self.media_codec_frame, textvariable=self.media_codec_var,
                         values=AVAILABLE_CODECS, state="readonly", width=10).pack(padx=5, pady=5)
        else:
            self.media_no_codec_label = ttk.Label(self.media_codec_frame, text=self._tr("media_install"))
            self.media_no_codec_label.pack(pady=5)

        self.media_file_frame = ttk.LabelFrame(media_frame, text=self._tr("media_file_frame"))
        self.media_file_frame.pack(pady=5, padx=10, fill=tk.X)
        self.media_input_btn = ttk.Button(self.media_file_frame, text=self._tr("media_select_input"),
                                          command=self._media_select_input)
        self.media_input_btn.pack(pady=5)
        self.media_input_label = ttk.Label(self.media_file_frame, text=self._tr("iii_not_selected"), foreground="gray")
        self.media_input_label.pack(pady=2)

        self.media_data_frame = ttk.LabelFrame(media_frame, text=self._tr("media_data_frame"))
        self.media_data_frame.pack(pady=5, padx=10, fill=tk.X)
        self.media_data_btn = ttk.Button(self.media_data_frame, text=self._tr("media_select_data"),
                                         command=self._media_select_data)
        self.media_data_btn.pack(pady=5)
        self.media_data_label = ttk.Label(self.media_data_frame, text=self._tr("iii_not_selected"), foreground="gray")
        self.media_data_label.pack(pady=2)

        self.media_out_frame = ttk.LabelFrame(media_frame, text=self._tr("media_output_frame"))
        self.media_out_frame.pack(pady=5, padx=10, fill=tk.X)
        self.media_output_btn = ttk.Button(self.media_out_frame, text=self._tr("media_select_output"),
                                           command=self._media_select_output)
        self.media_output_btn.pack(pady=5)
        self.media_output_label = ttk.Label(self.media_out_frame, text=self._tr("iii_not_specified"), foreground="gray")
        self.media_output_label.pack(pady=2)

        media_action_frame = ttk.Frame(media_frame)
        media_action_frame.pack(pady=10)
        self.media_action_btn = ttk.Button(media_action_frame, text=self._tr("media_execute"),
                                           command=self._media_process, width=20)
        self.media_action_btn.pack()

        self.media_status_label = ttk.Label(media_frame, text=self._tr("media_ready"), foreground="gray")
        self.media_status_label.pack(pady=5)

        self.scan_file_frame = ttk.LabelFrame(scan_frame, text=self._tr("scan_file_frame"))
        self.scan_file_frame.pack(pady=5, padx=10, fill=tk.X)
        self.scan_file_btn = ttk.Button(self.scan_file_frame, text=self._tr("scan_select_file"),
                                        command=self._scan_select_file)
        self.scan_file_btn.pack(pady=5)
        self.scan_file_label = ttk.Label(self.scan_file_frame, text=self._tr("iii_not_selected"), foreground="gray")
        self.scan_file_label.pack(pady=2)

        self.scan_opts_frame = ttk.LabelFrame(scan_frame, text=self._tr("scan_opts_frame"))
        self.scan_opts_frame.pack(pady=5, padx=10, fill=tk.X)
        self.scan_alpha_var = tk.BooleanVar(value=True)
        self.scan_alpha_chk = ttk.Checkbutton(self.scan_opts_frame, text=self._tr("scan_alpha"),
                                              variable=self.scan_alpha_var)
        self.scan_alpha_chk.pack(anchor=tk.W, padx=5, pady=2)
        self.scan_rgb_var = tk.BooleanVar(value=True)
        self.scan_rgb_chk = ttk.Checkbutton(self.scan_opts_frame, text=self._tr("scan_rgb"),
                                            variable=self.scan_rgb_var)
        self.scan_rgb_chk.pack(anchor=tk.W, padx=5, pady=2)
        layers_f = ttk.Frame(self.scan_opts_frame)
        layers_f.pack(fill=tk.X, padx=5, pady=5)
        self.scan_depth_label = ttk.Label(layers_f, text=self._tr("scan_depth"))
        self.scan_depth_label.pack(side=tk.LEFT)
        self.scan_layers_var = tk.IntVar(value=4)
        ttk.Spinbox(layers_f, from_=1, to=8, textvariable=self.scan_layers_var,
                    width=5).pack(side=tk.LEFT, padx=5)

        scan_btn_f = ttk.Frame(scan_frame)
        scan_btn_f.pack(pady=10)
        self.scan_btn = ttk.Button(scan_btn_f, text=self._tr("scan_btn"), command=self._scan_process, width=20)
        self.scan_btn.pack()

        self.scan_result_frame = ttk.LabelFrame(scan_frame, text=self._tr("scan_result_frame"))
        self.scan_result_frame.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)
        self.scan_result_text = scrolledtext.ScrolledText(self.scan_result_frame, height=12, font=("Courier", 9))
        self.scan_result_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.scan_status_label = ttk.Label(scan_frame, text=self._tr("ready"), foreground="gray")
        self.scan_status_label.pack(pady=5)

        self.debug_opt_frame = ttk.LabelFrame(debug_frame, text=self._tr("debug_options"))
        self.debug_opt_frame.pack(pady=5, padx=10, fill=tk.X)
        self.debug_chk = ttk.Checkbutton(self.debug_opt_frame, text=self._tr("debug_mode"),
                                         variable=self.debug_var)
        self.debug_chk.pack(anchor=tk.W)
        self.debug_clear_btn = ttk.Button(self.debug_opt_frame, text=self._tr("debug_clear"),
                                          command=lambda: self.debug_log.delete(1.0, tk.END))
        self.debug_clear_btn.pack(anchor=tk.W, pady=2)

        self.debug_log = scrolledtext.ScrolledText(debug_frame, height=10, font=("Courier", 9))
        self.debug_log.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)

        self.status_label = ttk.Label(self.root, text=self._tr("ready"), relief=tk.SUNKEN, anchor=tk.W)
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
        self.file_label.config(text=self._tr("no_file"))
        self._update_core_settings()

        if self.mode_var.get() == "encode":
            self.btn_select.config(text=self._tr("select_encode_file"))
            self.file_label.config(text=self._tr("encode_hint"))
        else:
            self.btn_select.config(text=self._tr("select_decode_file"))
            self.file_label.config(text=self._tr("decode_hint"))

    def select_file(self):
        if self.mode_var.get() == "encode":
            ft = [("All files", "*.*"), ("Text files", "*.txt"), ("Binary files", "*.bin")]
            filename = filedialog.askopenfilename(filetypes=ft, title=self._tr("select_encode"))
        else:
            ft = [("Image files", "*.png *.webp *.bmp"), ("PNG image", "*.png"),
                  ("WebP image", "*.webp"), ("BMP image", "*.bmp")]
            filename = filedialog.askopenfilename(filetypes=ft, title=self._tr("select_decode_img"))

        if filename:
            self.load_file(filename)

    def load_file(self, filename):
        if not os.path.exists(filename):
            messagebox.showerror(self._tr("error"), self._tr("err_file_not_found"))
            return

        self.input_file_path = filename
        self.file_label.config(text=self._tr("file_info", os.path.basename(filename), self._format_size(os.path.getsize(filename))))

        if self.mode_var.get() == "encode":
            self._load_encode_file(filename)
        else:
            self._load_decode_file(filename)

    def _format_size(self, size):
        units = [self._tr("unit_b"), self._tr("unit_kb"), self._tr("unit_mb"), self._tr("unit_gb")]
        for unit in units:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} {self._tr('unit_tb')}"

    def _load_encode_file(self, filename):
        try:
            size = os.path.getsize(filename)
            if size > 1024 * 1024:
                if not messagebox.askyesno(self._tr("notice"), self._tr("warn_big_file", self._format_size(size))):
                    self.text_area.delete(1.0, tk.END)
                    self.text_area.insert(tk.END, self._tr("warn_large_file", self._format_size(size)))
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
                    self.text_area.insert(tk.END, self._tr("warn_text_preview", len(lines)))
                    self.text_area.insert(tk.END, '\n'.join(lines[:50]))
                    self.text_area.insert(tk.END, self._tr("warn_more_lines", len(lines) - 50))
                else:
                    self.text_area.insert(tk.END, text)
            except UnicodeDecodeError:
                self.text_area.delete(1.0, tk.END)
                self.text_area.insert(tk.END, self._tr("warn_binary", self._format_size(len(raw_data)), self._calculate_sha256(raw_data)))
        except Exception as e:
            messagebox.showerror(self._tr("error"), self._tr("err_read_failed", e))
            return

        self.status_label.config(text=self._tr("file_loaded", os.path.basename(filename)))

    def _calculate_sha256(self, data):
        import hashlib
        return hashlib.sha256(data).hexdigest()[:16] + "...\u200b"

    def _load_decode_file(self, filename):
        self.text_area.delete(1.0, tk.END)

        try:
            from PIL import Image
            img = Image.open(filename)
            self.text_area.insert(tk.END, self._tr("image_info"))
            self.text_area.insert(tk.END, self._tr("image_dims", img.size[0], img.size[1]))
            self.text_area.insert(tk.END, self._tr("image_mode", img.mode))
            self.text_area.insert(tk.END, self._tr("image_format", img.format))
            self.text_area.insert(tk.END, self._tr("image_decode_hint"))
        except Exception as e:
            self.text_area.insert(tk.END, self._tr("err_read_image", e))

        self.status_label.config(text=self._tr("file_loaded", os.path.basename(filename)))

    def process_file(self):
        if not self.input_file_path:
            messagebox.showwarning(self._tr("notice"), self._tr("err_no_file"))
            return

        if self.encryption_var.get() and self.mode_var.get() == "encode":
            password = self.password_var.get()
            confirm = self.confirm_password_var.get()
            if not password:
                messagebox.showwarning(self._tr("notice"), self._tr("err_encrypt_no_password"))
                return
            if password != confirm:
                messagebox.showwarning(self._tr("notice"), self._tr("err_password_mismatch"))
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
            self.root.after(0, lambda e=e: messagebox.showerror(self._tr("error"), str(e)))
        finally:
            self.root.after(0, self._enable_buttons)
            self.root.after(0, lambda: self.progress_var.set(100))

    def _request_password_and_decode(self):
        try:
            is_encrypted = self.core.check_encryption(self.input_file_path)
            if is_encrypted:
                password = simpledialog.askstring(self._tr("password"),
                                                  self._tr("err_password_hint"),
                                                  parent=self.root, show='*')
                if password is None:
                    self._enable_buttons()
                    return
            else:
                password = None
            threading.Thread(target=self._decode_with_password, args=(password,)).start()
        except Exception as e:
            messagebox.showerror(self._tr("error"), str(e))
            self._enable_buttons()

    def _decode_with_password(self, password):
        try:
            output_dir = self.output_dir_var.get() if self.output_dir_var.get() else None
            result = self.core.decode(self.input_file_path, output_dir, password=password)
            self.root.after(0, lambda: self._decode_callback(result))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror(self._tr("error"), str(e)))

    def _enable_buttons(self):
        self.btn_action.config(state=tk.NORMAL)
        self.btn_cancel.config(state=tk.NORMAL)

    def _encode(self):
        try:
            output_dir = self.output_dir_var.get() if self.output_dir_var.get() else None
            result = self.core.encode(self.input_file_path, output_dir)
            self.root.after(0, lambda: self._encode_callback(result))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror(self._tr("error"), str(e)))

    def _encode_callback(self, result):
        self.core.clear_sensitive_data()
        if result['success']:
            self.output_file_path = result['output_path']

            self.text_area.delete(1.0, tk.END)
            self.text_area.insert(tk.END, self._tr("encode_success"))
            self.text_area.insert(tk.END, self._tr("encode_saved", result['output_path']))
            self.text_area.insert(tk.END, self._tr("encode_dims", result.get('width', '?'), result.get('height', '?')))
            self.text_area.insert(tk.END, self._tr("encode_format", self.output_format_var.get()))
            self.text_area.insert(tk.END, self._tr("encode_file_size", self._format_size(result.get('size', 0))))
            self.text_area.insert(tk.END, self._tr("encode_time", result.get('elapsed', 0)))

            if result.get('chunked'):
                self.text_area.insert(tk.END, self._tr("encode_chunks", result.get('num_chunks', 0)))

            if self.compress_var.get():
                self.text_area.insert(tk.END, self._tr("encode_compress", self.compress_level_var.get()))

            if self.encryption_var.get():
                self.text_area.insert(tk.END, self._tr("encode_encryption"))
                if self.hint_var.get():
                    self.text_area.insert(tk.END, self._tr("encode_hint_warn", self.hint_var.get()))

            if self.integrity_var.get() and result.get('sha256'):
                self.text_area.insert(tk.END, self._tr("encode_sha", result['sha256']))

            self.status_label.config(text=self._tr("file_loaded", os.path.basename(result['output_path'])))
        else:
            messagebox.showerror(self._tr("error"), self._tr("err_encode_failed", result.get('error', '?')))
            self.status_label.config(text=self._tr("status_error"))

    def _decode_callback(self, result):
        self.core.clear_sensitive_data()
        if result['success']:
            self.output_file_path = result['output_path']

            self.text_area.delete(1.0, tk.END)
            self.text_area.insert(tk.END, self._tr("decode_success"))

            try:
                with open(result['output_path'], 'rb') as f:
                    data = f.read()

                try:
                    text = data.decode('utf-8')
                    lines = text.splitlines()
                    if len(lines) > 50:
                        self.text_area.insert(tk.END, self._tr("warn_text_preview", len(lines)))
                        self.text_area.insert(tk.END, '\n'.join(lines[:50]))
                        self.text_area.insert(tk.END, self._tr("warn_text_more", len(lines) - 50))
                    else:
                        self.text_area.insert(tk.END, text)
                except UnicodeDecodeError:
                    self.text_area.insert(tk.END, self._tr("warn_binary", self._format_size(len(data)), ''))
            except:
                self.text_area.insert(tk.END, self._tr("decode_saved", result['output_path']))

            self.text_area.insert(tk.END, self._tr("decode_saved", result['output_path']))
            self.text_area.insert(tk.END, self._tr("decode_size", self._format_size(result.get('size', 0))))

            if result.get('chunked'):
                self.text_area.insert(tk.END, self._tr("decode_chunks", result.get('num_chunks', 0)))

            self.status_label.config(text=self._tr("file_loaded", os.path.basename(result['output_path'])))
        else:
            messagebox.showerror(self._tr("error"), self._tr("err_decode_failed", result.get('error', '?')))
            self.status_label.config(text=self._tr("status_error"))

    def batch_encode(self):
        if not self.batch_files:
            messagebox.showwarning(self._tr("notice"), self._tr("err_batch_empty"))
            return

        if self.encryption_var.get():
            password = self.password_var.get()
            confirm = self.confirm_password_var.get()
            if not password:
                messagebox.showwarning(self._tr("notice"), self._tr("err_encrypt_no_password"))
                return
            if password != confirm:
                messagebox.showwarning(self._tr("notice"), self._tr("err_password_mismatch"))
                return

        self._update_core_settings()
        threading.Thread(target=self._batch_encode_thread).start()

    def _batch_encode_thread(self):
        try:
            output_dir = self.output_dir_var.get() if self.output_dir_var.get() else None
            results = self.core.batch_encode(self.batch_files, output_dir)
            success_count = sum(1 for r in results if r.get('success', False))
            self.root.after(0, lambda: messagebox.showinfo(
                self._tr("batch_complete"),
                self._tr("batch_summary", len(results), success_count, len(results) - success_count)))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror(self._tr("error"), str(e)))

    def batch_decode(self):
        if not self.batch_files:
            messagebox.showwarning(self._tr("notice"), self._tr("err_batch_empty"))
            return

        password = None
        try:
            any_encrypted = any(self.core.check_encryption(f) for f in self.batch_files)
            if any_encrypted:
                password = simpledialog.askstring(self._tr("password"),
                                                  self._tr("err_batch_password_hint"),
                                                  parent=self.root, show='*')
                if password is None:
                    return
        except Exception as e:
            messagebox.showerror(self._tr("error"), str(e))
            return

        self._update_core_settings()
        threading.Thread(target=self._batch_decode_thread, args=(password,)).start()

    def _batch_decode_thread(self, password):
        try:
            output_dir = self.output_dir_var.get() if self.output_dir_var.get() else None
            results = self.core.batch_decode(self.batch_files, output_dir, password)
            success_count = sum(1 for r in results if r.get('success', False))
            self.root.after(0, lambda: messagebox.showinfo(
                self._tr("batch_complete"),
                self._tr("batch_summary", len(results), success_count, len(results) - success_count)))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror(self._tr("error"), str(e)))

    # ─── Image-in-Image ────────────────────────────────────────────────

    def _iii_select_container(self):
        path = filedialog.askopenfilename(title=self._tr("select_container"),
                                          filetypes=[("Image files", "*.png *.webp *.bmp")])
        if path:
            self.iii_container_path = path
            self.iii_container_label.config(text=os.path.basename(path))

    def _iii_select_secret(self):
        path = filedialog.askopenfilename(title=self._tr("select_secret"),
                                          filetypes=[("Image files", "*.png *.jpg *.jpeg *.webp *.bmp")])
        if path:
            self.iii_secret_path = path
            self.iii_secret_label.config(text=os.path.basename(path))

    def _iii_select_output(self):
        path = filedialog.asksaveasfilename(title=self._tr("save_as"),
                                            defaultextension=".png",
                                            filetypes=[("PNG image", "*.png")])
        if path:
            self.iii_output_path = path
            self.iii_output_label.config(text=os.path.basename(path))

    def _iii_encode(self):
        if not self.iii_container_path or not self.iii_secret_path:
            messagebox.showwarning(self._tr("notice"), self._tr("err_select_container"))
            return
        if not self.iii_output_path:
            messagebox.showwarning(self._tr("notice"), self._tr("err_select_output"))
            return

        self.iii_result_text.delete(1.0, tk.END)
        self.iii_result_text.insert(tk.END, self._tr("iii_working") + "\n")
        self.iii_status_label.config(text=self._tr("iii_working_short"))

        def task():
            try:
                result = self.core.encode_image_in_image(
                    self.iii_container_path, self.iii_secret_path,
                    self.iii_output_path, use_alpha=self.iii_use_alpha_var.get()
                )
                self.root.after(0, lambda: self._iii_callback(result))
            except Exception as e:
                self.root.after(0, lambda: self._iii_callback({'success': False, 'error': str(e)}))

        threading.Thread(target=task, daemon=True).start()

    def _iii_decode(self):
        path = self.iii_container_path
        if not path:
            path = filedialog.askopenfilename(title=self._tr("select_container"),
                                              filetypes=[("PNG image", "*.png")])
            if not path:
                return

        if not self.iii_output_path:
            self.iii_output_path = filedialog.asksaveasfilename(
                title=self._tr("save_as"),
                defaultextension=".png",
                filetypes=[("PNG image", "*.png")])
            if not self.iii_output_path:
                return

        self.iii_result_text.delete(1.0, tk.END)
        self.iii_result_text.insert(tk.END, self._tr("iii_decode_working") + "\n")
        self.iii_status_label.config(text=self._tr("iii_working_short"))

        def task():
            try:
                result = self.core.decode_image_in_image(
                    path, self.iii_output_path, use_alpha=self.iii_use_alpha_var.get(),
                    restore_container=self.iii_restore_var.get()
                )
                self.root.after(0, lambda: self._iii_callback(result))
            except Exception as e:
                self.root.after(0, lambda: self._iii_callback({'success': False, 'error': str(e)}))

        threading.Thread(target=task, daemon=True).start()

    def _iii_callback(self, result):
        self.iii_result_text.delete(1.0, tk.END)
        if result['success']:
            self.iii_result_text.insert(tk.END, self._tr("iii_success") + "\n\n")
            self.iii_result_text.insert(tk.END, self._tr("iii_saved", result['output_path']) + "\n")
            secret_size = result.get('secret_size', '?')
            if isinstance(secret_size, tuple):
                self.iii_result_text.insert(tk.END, self._tr("iii_result_size", secret_size[0], secret_size[1]))
            else:
                self.iii_result_text.insert(tk.END, self._tr("iii_secret_size", str(secret_size)) + "\n")
            if result.get('alpha_preserved'):
                self.iii_result_text.insert(tk.END, self._tr("iii_alpha_saved") + "\n")
            if result.get('restored_container'):
                self.iii_result_text.insert(tk.END, self._tr("iii_container_restored", result['restored_container']) + "\n")
            self.iii_status_label.config(text=self._tr("iii_done"))
        else:
            self.iii_result_text.insert(tk.END, self._tr("iii_error", result.get('error', '?')) + "\n")
            self.iii_status_label.config(text=self._tr("status_error"))

    # ─── Media Steganography ───────────────────────────────────────────

    def _media_select_input(self):
        ext = []
        codec = self.media_codec_var.get()
        if codec == 'GIF':
            ext = [("GIF files", "*.gif")]
        elif codec == 'MP4':
            ext = [("MP4 files", "*.mp4")]
        elif codec == 'MP3':
            ext = [("MP3 files", "*.mp3")]
        path = filedialog.askopenfilename(title=self._tr("select_media"), filetypes=ext)
        if path:
            self.media_input_path = path
            self.media_input_label.config(text=os.path.basename(path))

    def _media_select_data(self):
        path = filedialog.askopenfilename(title=self._tr("select_data"),
                                          filetypes=[("All files", "*.*")])
        if path:
            self.media_data_file = path
            self.media_data_label.config(text=os.path.basename(path))

    def _media_select_output(self):
        codec = self.media_codec_var.get()
        ext = codec.lower() if codec else 'bin'
        path = filedialog.asksaveasfilename(title=self._tr("select_save_as"),
                                            defaultextension=f".{ext}",
                                            filetypes=[(f"{codec} files", f"*.{ext}")])
        if path:
            self.media_output_path = path
            self.media_output_label.config(text=os.path.basename(path))

    def _media_process(self):
        if not self.media_input_path:
            messagebox.showwarning(self._tr("notice"), self._tr("err_media_no_input"))
            return

        codec = self.media_codec_var.get()
        mode = self.media_mode_var.get()

        if mode == "encode" and not self.media_data_file:
            messagebox.showwarning(self._tr("notice"), self._tr("err_media_no_data"))
            return

        if not self.media_output_path:
            ext = codec.lower() if mode == "encode" else "bin"
            out = filedialog.asksaveasfilename(title=self._tr("select_save_as"),
                                               defaultextension=f".{ext}",
                                               filetypes=[("All files", "*.*")])
            if not out:
                return
            self.media_output_path = out
            self.media_output_label.config(text=os.path.basename(out))

        media = MediaSteganography()
        self.media_status_label.config(text=self._tr("media_working"))

        def task():
            try:
                if mode == "encode":
                    with open(self.media_data_file, 'rb') as f:
                        data = f.read()

                    if codec == 'GIF':
                        result = media.encode_gif(self.media_input_path, data, self.media_output_path)
                    elif codec == 'MP4':
                        result = media.encode_mp4(self.media_input_path, data, self.media_output_path)
                    elif codec == 'MP3':
                        result = media.encode_mp3(self.media_input_path, data, self.media_output_path)
                    else:
                        result = {'success': False, 'error': f'Unsupported codec: {codec}'}
                else:
                    if codec == 'GIF':
                        result = media.decode_gif(self.media_input_path, self.media_output_path)
                    elif codec == 'MP4':
                        result = media.decode_mp4(self.media_input_path, self.media_output_path)
                    elif codec == 'MP3':
                        result = media.decode_mp3(self.media_input_path, self.media_output_path)
                    else:
                        result = {'success': False, 'error': f'Unsupported codec: {codec}'}

                self.root.after(0, lambda: self._media_callback(result))
            except Exception as e:
                self.root.after(0, lambda: self._media_callback({'success': False, 'error': str(e)}))

        threading.Thread(target=task, daemon=True).start()

    def _media_callback(self, result):
        if result['success']:
            self.media_status_label.config(text=self._tr("media_done"))
            messagebox.showinfo(self._tr("batch_complete"), self._tr("media_success", result['output_path']))
        else:
            self.media_status_label.config(text=self._tr("status_error"))
            messagebox.showerror(self._tr("error"), self._tr("media_error", result.get('error', '?')))

    # ─── Scanner ────────────────────────────────────────────────────

    def _scan_select_file(self):
        path = filedialog.askopenfilename(title=self._tr("select_scan"),
                                          filetypes=[("Image files", "*.png *.webp *.bmp *.tiff")])
        if path:
            self.scan_file_path = path
            self.scan_file_label.config(text=os.path.basename(path))
            self.scan_status_label.config(text=self._tr("status_ready"))

    def _scan_process(self):
        if not hasattr(self, 'scan_file_path') or not self.scan_file_path:
            messagebox.showwarning(self._tr("notice"), self._tr("err_scan_no_file"))
            return

        self.scan_result_text.delete(1.0, tk.END)
        self.scan_result_text.insert(tk.END, self._tr("scan_working") + "\n")
        self.scan_status_label.config(text=self._tr("status_scanning"))

        def task():
            try:
                results = self.core.scan_for_header(
                    self.scan_file_path,
                    scan_alpha=self.scan_alpha_var.get(),
                    scan_rgb=self.scan_rgb_var.get(),
                    max_layers=self.scan_layers_var.get()
                )
                self.root.after(0, lambda: self._scan_callback(results))
            except Exception as e:
                self.root.after(0, lambda: self._scan_callback([], str(e)))

        threading.Thread(target=task, daemon=True).start()

    def _scan_callback(self, results, error=None):
        self.scan_result_text.delete(1.0, tk.END)
        if error:
            self.scan_result_text.insert(tk.END, self._tr("media_error", error) + "\n")
            self.scan_status_label.config(text=self._tr("status_error"))
            return

        if not results:
            self.scan_result_text.insert(tk.END, self._tr("scan_no_results") + "\n")
            self.scan_result_text.insert(tk.END, self._tr("scan_no_reasons") + "\n")
            self.scan_status_label.config(text=self._tr("status_not_found"))
        else:
            self.scan_result_text.insert(tk.END, self._tr("scan_found", len(results)))
            for r in results:
                htype = r['header'].get('type', '?')
                self.scan_result_text.insert(tk.END, self._tr("scan_channel", r['channel']))
                self.scan_result_text.insert(tk.END, self._tr("scan_lsb", r['bits']))
                self.scan_result_text.insert(tk.END, self._tr("scan_type", htype))
                self.scan_result_text.insert(tk.END, self._tr("scan_sig", r['header']['signature']))
                self.scan_result_text.insert(tk.END, self._tr("scan_ver", r['header']['version']))
                self.scan_result_text.insert(tk.END, self._tr("scan_sep"))
            self.scan_status_label.config(text=self._tr("status_found_headers", len(results)))


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
