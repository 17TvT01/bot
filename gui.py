# -*- coding: utf-8 -*-
"""Modernized Tkinter GUI for the assistant with chat bubbles, sidebar,
light/dark themes, and quick actions."""

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import tkinter.font as tkfont
import time
import unicodedata
import re
import assistant
from features.ai_enhancements import get_ai_assistant
try:
    from features import gemini_bridge
except Exception:
    gemini_bridge = None

# Safe optional import for ChatGPT bridge used in settings
try:
    from features import chatgpt_bridge
except Exception:
    chatgpt_bridge = None

# Optional voice features (TTS/STT)
try:
    from features import voice as voice_mod
except Exception:
    voice_mod = None

# Lazy import for reminder feature
_reminder_manager = None


def get_reminder_manager():
    global _reminder_manager
    if _reminder_manager is None:
        try:
            from features.reminder import get_reminder_manager as get_rm
            _reminder_manager = get_rm()
        except ImportError:
            return None
    return _reminder_manager


def repair_vi(s: str) -> str:
    """Best-effort fix of mojibake Vietnamese strings to proper UTF-8 text."""
    if not isinstance(s, str):
        return s
    mapping = {
        'Tr��� lA� ���o': 'Trợ lý ảo',
        'Giao di���n': 'Giao diện',
        'Tr��� giA�p': 'Trợ giúp',
        'Gi��>i thi���u': 'Giới thiệu',
        'ThoA�t': 'Thoát',
        'Ch��� �`��T t��`i': 'Chế độ tối',
        'TA-nh n��ng': 'Tính năng',
        'Nh��_c nh��Y': 'Nhắc nhở',
        '�?���n gi��?': 'Đến giờ:',
        'Th��?i gian': 'Thời gian',
        '�?ang t���i tA-nh n��ng': 'Đang tải tính năng',
        'G��-i': 'Gửi',
        'Nh��-p yA�u c��\u0015u c��\u0015a b���n...': 'Nhập yêu cầu của bạn...',
        '�?ang x��- lA��?�': 'Đang xử lý',
        'B���n: ': 'Bạn: ',
        'Tr��� lA�: ': 'Trợ lý: ',
    }
    out = s
    try:
        for k, v in mapping.items():
            out = out.replace(k, v)
    except Exception:
        return s
    return out


class ChatView(ttk.Frame):
    """Scrollable chat with rounded bubbles."""

    def __init__(self, parent, palette):
        super().__init__(parent)
        self.palette = palette
        self.canvas = tk.Canvas(self, highlightthickness=0, bg=self.palette['panel'])
        self.scroll = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scroll.set)
        self.inner = ttk.Frame(self)
        self.inner_id = self.canvas.create_window((0, 0), window=self.inner, anchor='nw')

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.inner.bind('<Configure>', self._on_frame_configure)
        self.canvas.bind('<Configure>', self._on_canvas_configure)

        self.font = tkfont.Font(family='Segoe UI', size=10)
        self.messages = []
        # Typing indicator state
        self._typing_row = None
        self._typing_canvas = None
        self._typing_after = None
        self._typing_phase = 0

        # Context menu for copy
        self._rc_text = None
        self._menu = tk.Menu(self, tearoff=0)
        self._menu.add_command(label="Copy", command=self._copy_selected_text)

    def set_palette(self, pal):
        self.palette = pal
        self.canvas.configure(bg=self.palette['panel'])
        self.redraw()

    def clear(self):
        for child in self.inner.winfo_children():
            child.destroy()
        self.messages.clear()
        self.canvas.yview_moveto(0)
        self.hide_typing_indicator()

    def add_message(self, role, text):
        align = 'e' if role == 'user' else 'w'
        bubble_bg = self.palette['primary'] if role == 'user' else self.palette['panel']
        bubble_fg = '#FFFFFF' if role == 'user' else self.palette['text']
        border = '' if role == 'user' else self.palette['border']

        row = ttk.Frame(self.inner)
        row.pack(fill=tk.X, anchor=align, pady=6)

        bubble = tk.Canvas(row, highlightthickness=0, bd=0, bg=self.palette['panel'], cursor='arrow')
        bubble.pack(side=tk.RIGHT if role == 'user' else tk.LEFT, padx=6)
        try:
            bubble._role = role
        except Exception:
            pass

        maxw = max(280, int(self.canvas.winfo_width() * 0.6)) if self.canvas.winfo_width() > 1 else 520
        timestamp = time.strftime('%H:%M')
        prefix = 'Bạn: ' if role == 'user' else 'Trợ lý: '
        display_text = repair_vi(f"{prefix}{text}\n[{timestamp}]")
        text_id = bubble.create_text(12, 12, anchor='nw', text=display_text, font=self.font,
                                     fill=bubble_fg, width=maxw)
        bubble.update_idletasks()
        x1, y1, x2, y2 = bubble.bbox(text_id)
        pad = 10
        rx = 12
        rect = self._round_rect(bubble, x1 - pad, y1 - pad, x2 + pad, y2 + pad, rx,
                                 fill=bubble_bg, outline=border)
        bubble.tag_lower(rect, text_id)
        bubble.configure(width=x2 + pad + 4, height=y2 + pad + 4)

        # Right-click to copy original message text
        bubble.bind('<Button-3>', lambda e, t=text: self._show_copy_menu(e, t))

        self.messages.append((row, bubble, role))
        self.after(10, lambda: self.canvas.yview_moveto(1.0))

    def remove_pending_marker(self):
        # Not storing markers separately; nothing to remove.
        pass

    def show_typing_indicator(self):
        try:
            self.hide_typing_indicator()
            self._typing_row = ttk.Frame(self.inner)
            self._typing_row.pack(fill=tk.X, anchor='w', pady=6)
            self._typing_canvas = tk.Canvas(self._typing_row, highlightthickness=0, bd=0, bg=self.palette['panel'])
            self._typing_canvas.pack(side=tk.LEFT, padx=6)
            self._typing_phase = 0
            self._animate_typing()
        except Exception:
            pass

    def hide_typing_indicator(self):
        try:
            if self._typing_after is not None:
                try:
                    self.after_cancel(self._typing_after)
                except Exception:
                    pass
                self._typing_after = None
            if self._typing_row is not None:
                self._typing_row.destroy()
                self._typing_row = None
                self._typing_canvas = None
        except Exception:
            pass

    def _animate_typing(self):
        if self._typing_canvas is None:
            return
        try:
            c = self._typing_canvas
            c.delete('all')
            maxw = max(280, int(self.canvas.winfo_width() * 0.6)) if self.canvas.winfo_width() > 1 else 520
            dots = '.' * (1 + (self._typing_phase % 3))
            text = repair_vi(f"Đang xử lý {dots}")
            bubble_bg = self.palette['panel']
            bubble_fg = self.palette['text']
            text_id = c.create_text(12, 12, anchor='nw', text=text, font=self.font, fill=bubble_fg, width=maxw)
            c.update_idletasks()
            x1, y1, x2, y2 = c.bbox(text_id)
            pad = 10
            rx = 12
            rect = self._round_rect(c, x1 - pad, y1 - pad, x2 + pad, y2 + pad, rx,
                                    fill=bubble_bg, outline=self.palette['border'])
            c.tag_lower(rect, text_id)
            c.configure(width=x2 + pad + 4, height=y2 + pad + 4)
            self._typing_phase += 1
            self._typing_after = self.after(500, self._animate_typing)
        except Exception:
            pass

    def _prefix(self, role, text):
        return ("Bạn: " if role == 'user' else "Trợ lý: ") + text

    def _round_rect(self, c, x1, y1, x2, y2, r, **kwargs):
        points = [
            x1 + r, y1,
            x2 - r, y1,
            x2, y1,
            x2, y1 + r,
            x2, y2 - r,
            x2, y2,
            x2 - r, y2,
            x1 + r, y2,
            x1, y2,
            x1, y2 - r,
            x1, y1 + r,
            x1, y1
        ]
        return c.create_polygon(points, smooth=True, **kwargs)

    def _on_frame_configure(self, _):
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.inner_id, width=event.width)
        self.redraw()

    def redraw(self):
        for msg in self.messages:
            if isinstance(msg, tuple):
                if len(msg) == 3:
                    _, bubble, role = msg
                elif len(msg) == 2:
                    _, bubble = msg
                    role = 'assistant'
                else:
                    continue
            else:
                try:
                    bubble = msg.get('bubble')
                    role = msg.get('role', 'assistant')
                except Exception:
                    continue
            items = bubble.find_all()
            if not items:
                continue
            text_id = items[-1]
            text = repair_vi(bubble.itemcget(text_id, 'text'))
            role = 'user' if text.startswith('Bạn: ') else 'assistant'
            bubble.delete('all')
            try:
                role = getattr(bubble, '_role', role)
            except Exception:
                pass
            maxw = max(280, int(self.canvas.winfo_width() * 0.6)) if self.canvas.winfo_width() > 1 else 520
            bubble_bg = self.palette['primary'] if role == 'user' else self.palette['panel']
            bubble_fg = '#FFFFFF' if role == 'user' else self.palette['text']
            border = '' if role == 'user' else self.palette['border']
            text_id = bubble.create_text(12, 12, anchor='nw', text=text, font=self.font, fill=bubble_fg, width=maxw)
            bubble.update_idletasks()
            x1, y1, x2, y2 = bubble.bbox(text_id)
            pad = 10
            rx = 12
            rect = self._round_rect(bubble, x1 - pad, y1 - pad, x2 + pad, y2 + pad, rx,
                                     fill=bubble_bg, outline=border)
            bubble.tag_lower(rect, text_id)
            bubble.configure(width=x2 + pad + 4, height=y2 + pad + 4)

    def _show_copy_menu(self, event, text):
        try:
            self._rc_text = text
            self._menu.tk_popup(event.x_root, event.y_root)
        finally:
            self._menu.grab_release()

    def _copy_selected_text(self):
        if self._rc_text is None:
            return
        try:
            self.clipboard_clear()
            self.clipboard_append(self._rc_text)
        except Exception:
            pass


class AssistantGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.processing = False
        self.pending_commands = []
        self.dark_mode = tk.BooleanVar(value=False)
        # Command history
        self.history = []
        self.history_index = -1

        # Timing
        self.start_time = time.time()

        # Window basics
        root.title("Trợ lý ảo – Trải nghiệm hiện đại")
        root.title("Tro ly ao — Giao dien hien dai")
        root.geometry("980x640")
        root.minsize(720, 480)
        root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Theme + UI
        self._init_style()
        self._create_ui()

        # Initial greeting
        self._assistant_message("Chào bạn! Đang khởi động...")
        self.root.update_idletasks()
        self.root.after(10, self._start_loading_features)

    # ========== Theme and styling ==========
    def _init_style(self):
        self.style = ttk.Style()
        base = 'clam' if 'clam' in self.style.theme_names() else self.style.theme_use()
        self.style.theme_use(base)

        self.palette_light = {
            'bg': '#F7F7FA',
            'panel': '#FFFFFF',
            'text': '#1F2328',
            'muted': '#57606A',
            'primary': '#0B84FF',
            'accent': '#00A37A',
            'border': '#D0D7DE'
        }
        self.palette_dark = {
            'bg': '#0D1117',
            'panel': '#161B22',
            'text': '#E6EDF3',
            'muted': '#8B949E',
            'primary': '#58A6FF',
            'accent': '#3FB950',
            'border': '#30363D'
        }
        self._apply_theme()

    def _apply_theme(self):
        pal = self.palette_dark if self.dark_mode.get() else self.palette_light
        self.root.configure(bg=pal['bg'])

        base_font = ('Segoe UI', 10)
        small_font = ('Segoe UI', 9)
        title_font = ('Segoe UI Semibold', 12)

        self.style.configure('TFrame', background=pal['bg'])
        self.style.configure('Card.TFrame', background=pal['panel'], relief='flat')
        self.style.configure('TLabel', background=pal['bg'], foreground=pal['text'], font=base_font)
        self.style.configure('Muted.TLabel', foreground=pal['muted'], background=pal['bg'], font=small_font)
        self.style.configure('Title.TLabel', background=pal['bg'], foreground=pal['text'], font=title_font)
        self.style.configure('TButton', font=base_font)
        self.style.configure('TEntry', fieldbackground=pal['panel'], foreground=pal['text'])
        self.style.map('TButton', background=[('active', pal['primary'])])
        self.style.configure(
            'Modern.Horizontal.TProgressbar',
            troughcolor=pal['panel'], background=pal['primary'],
            bordercolor=pal['panel'], lightcolor=pal['primary'], darkcolor=pal['primary']
        )

    def _on_toggle_theme(self):
        self._apply_theme()
        pal = self.palette_dark if self.dark_mode.get() else self.palette_light
        if hasattr(self, 'chat'):
            self.chat.set_palette(pal)

    # ========== UI creation ==========
    def _create_ui(self):
        pal = self.palette_dark if self.dark_mode.get() else self.palette_light

        # Menu
        menubar = tk.Menu(self.root)
        menu_file = tk.Menu(menubar, tearoff=0)
        menu_file.add_command(label="Clear Chat", command=self.clear_chat_action)
        menu_file.add_command(label="Exit", command=self.on_closing)
        menu_file.add_command(label="Thoát", command=self.on_closing)
        menubar.add_cascade(label="Tệp", menu=menu_file)

        menu_view = tk.Menu(menubar, tearoff=0)
        menu_view.add_checkbutton(label="Chế độ tối", onvalue=True, offvalue=False, variable=self.dark_mode, command=self._on_toggle_theme)
        menubar.add_cascade(label="Giao diện", menu=menu_view)

        menu_help = tk.Menu(menubar, tearoff=0)
        menu_help.add_command(label="Giới thiệu", command=lambda: messagebox.showinfo("Về", "Trợ lý ảo – Giao diện hiện đại"))
        menubar.add_cascade(label="Trợ giúp", menu=menu_help)
        # ChatGPT settings menu
        try:
            menu_gpt = tk.Menu(menubar, tearoff=0)
            menu_gpt.add_command(label="Thiết lập API Key...", command=self.open_chatgpt_settings)
        except Exception:
            pass

        self.root.config(menu=menubar)
        # Normalize Vietnamese UI texts post-creation
        try:
            # Window title
            self.root.title("Trợ lý ảo — Giao diện hiện đại")
            # Menubar cascades
            try:
                menubar.entryconfig(0, label='Tệp')
                menubar.entryconfig(1, label='Giao diện')
                menubar.entryconfig(2, label='Trợ giúp')
            except Exception:
                pass
            # File menu entries
            try:
                menu_file.entryconfig(0, label='Xóa hội thoại')
                menu_file.entryconfig(1, label='Thoát')
                if menu_file.index('end') is not None and menu_file.index('end') >= 2:
                    menu_file.delete(2)
            except Exception:
                pass
            # View menu entries
            try:
                menu_view.entryconfig(0, label='Chế độ tối')
            except Exception:
                pass
            # Help menu entries
            try:
                menu_help.entryconfig(0, label='Giới thiệu')
            except Exception:
                pass
        except Exception:
            pass

        # Header
        header = ttk.Frame(self.root, padding=(12, 10, 12, 0))
        header.pack(fill=tk.X)
        ttk.Label(header, text="Trợ lý ảo", style='Title.TLabel').pack(side=tk.LEFT)
        ttk.Checkbutton(header, text="Chế độ tối", variable=self.dark_mode, command=self._on_toggle_theme).pack(side=tk.RIGHT)

        # Body with resizable sidebar + content
        paned = ttk.Panedwindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(padx=12, pady=12, fill=tk.BOTH, expand=True)

        # Sidebar quick actions
        sidebar = ttk.Frame(paned, style='Card.TFrame', padding=12)
        ttk.Label(sidebar, text="Tính năng", style='Muted.TLabel').pack(anchor='w', pady=(0, 6))
        self._add_quick_button(sidebar, "🕑 Nhắc nhở", "nhắc nhở lúc 8h mai họp nhóm")
        self._add_quick_button(sidebar, "🧮 Máy tính", "tính 23 * 47")
        self._add_quick_button(sidebar, "☁️ Thời tiết", "thời tiết hôm nay")
        self._add_quick_button(sidebar, "💻 Hệ thống", "thông tin hệ thống")

        # Conversation card (content)
        card = ttk.Frame(paned, style='Card.TFrame', padding=12)
        # Add frames to paned window
        try:
            paned.add(sidebar, weight=1)
            paned.add(card, weight=4)
        except Exception:
            paned.add(sidebar)
            paned.add(card)

        # Chat view (bubble style)
        self.chat = ChatView(card, palette=pal)
        self.chat.pack(fill=tk.BOTH, expand=True)

        # Status row
        status_row = ttk.Frame(card)
        status_row.pack(fill=tk.X, pady=(2, 8))
        self.status_label = ttk.Label(status_row, text="Đang tải tính năng...", style='Muted.TLabel')
        self.status_label.pack(side=tk.LEFT)
        self.progress = ttk.Progressbar(status_row, mode='indeterminate', length=120, style='Modern.Horizontal.TProgressbar')
        self.progress.pack(side=tk.RIGHT)
        self.progress.start(24)

        # Quick toolbar with Settings (gear)
        try:
            toolbar = ttk.Frame(card)
            toolbar.pack(fill=tk.X, pady=(0, 4))
            ttk.Button(toolbar, text='⚙', width=3, command=self.open_settings).pack(side=tk.RIGHT)
        except Exception:
            pass

        # Input row
        input_row = ttk.Frame(card)
        input_row.pack(fill=tk.X)
        self.input_entry = ttk.Entry(input_row, state=tk.NORMAL)
        self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6)
        self.send_button = ttk.Button(input_row, text="Gửi", command=self.process_input, state=tk.DISABLED)
        self.send_button.pack(side=tk.RIGHT, padx=(8, 0))
        # Ensure button is enabled at startup
        try:
            self.send_button.config(state=tk.NORMAL)
        except Exception:
            pass

        # Placeholder
        self._placeholder_text = "Nhập yêu cầu của bạn..."
        self._apply_placeholder()

        # Bind events + shortcuts
        self.input_entry.bind("<Return>", self.process_input)
        self.input_entry.bind("<FocusIn>", self._on_focus_in)
        self.input_entry.bind("<FocusOut>", self._on_focus_out)
        self.root.bind_all('<Control-Return>', self.process_input)
        self.input_entry.bind('<Up>', self._on_history_up)
        self.input_entry.bind('<Down>', self._on_history_down)
        self.input_entry.bind('<KeyRelease>', self._update_char_count)
        self.root.bind_all('<Control-k>', lambda e: (self.input_entry.focus_set(), 'break'))
        self.root.bind_all('<Control-l>', lambda e: (self.chat.clear(), 'break'))
        # Voice shortcuts
        try:
            self.root.bind_all('<Control-m>', lambda e: (self.voice_input_action(), 'break'))
            self.root.bind_all('<Control-Shift-V>', lambda e: (self.speak_last_action(), 'break'))
        except Exception:
            pass

        # Application status bar (global)
        statusbar = ttk.Frame(self.root, padding=(12, 0, 12, 8))
        statusbar.pack(fill=tk.X, side=tk.BOTTOM)
        # Mic button on status bar for quick voice input (icon)
        try:
            ttk.Button(statusbar, text='🎤', width=3, command=self.voice_input_action).pack(side=tk.RIGHT, padx=(8,0))
        except Exception:
            pass
        ttk.Label(statusbar, text='Ctrl+Enter gui • Ctrl+L xoa', style='Muted.TLabel').pack(side=tk.LEFT)
        self.char_count_label = ttk.Label(statusbar, text='0 chars', style='Muted.TLabel')
        self.char_count_label.pack(side=tk.RIGHT)

        # Log UI creation time
        ui_time = time.time() - self.start_time
        print(f"UI created in: {ui_time:.2f} seconds")
        # Focus input to allow immediate typing
        try:
            self.input_entry.focus_set()
        except Exception:
            pass

    def open_settings(self):
        """Open a combined Settings dialog with tabs for ChatGPT and Gemini."""
        win = tk.Toplevel(self.root)
        try:
            win.title("Cai dat")
        except Exception:
            pass
        win.transient(self.root)
        win.grab_set()

        pal = self.palette_dark if self.dark_mode.get() else self.palette_light
        try:
            win.configure(bg=pal['bg'])
        except Exception:
            pass

        outer = ttk.Frame(win, padding=12)
        outer.pack(fill=tk.BOTH, expand=True)

        try:
            # Provider preference row
            pref_row = ttk.Frame(outer)
            pref_row.pack(fill=tk.X, pady=(0,8))
            ttk.Label(pref_row, text="Nhà cung cấp mặc định:").pack(side=tk.LEFT)
            providers = ["ChatGPT", "Gemini"]
            try:
                from features.provider_prefs import get_default_provider, set_default_provider  # type: ignore
                current = get_default_provider() or ""
            except Exception:
                current = ""
                set_default_provider = None  # type: ignore
            sel = tk.StringVar(value=("ChatGPT" if current == "chatgpt" else ("Gemini" if current == "gemini" else "")))
            combo = ttk.Combobox(pref_row, values=providers, state='readonly', width=12, textvariable=sel)
            combo.pack(side=tk.LEFT, padx=(8,0))
            def _on_sel(_evt=None):
                try:
                    val = sel.get().strip().lower()
                    if set_default_provider and val in ("chatgpt", "gemini"):
                        set_default_provider(val)
                except Exception:
                    pass
            combo.bind('<<ComboboxSelected>>', _on_sel)
        except Exception:
            pass

        try:
            notebook = ttk.Notebook(outer)
        except Exception:
            notebook = None

        # ChatGPT tab
        chatgpt_frame = ttk.Frame(outer if notebook is None else notebook, padding=12)
        ttk.Label(chatgpt_frame, text="OPENAI_API_KEY:").grid(row=0, column=0, sticky='w', pady=6)
        cg_api_var = tk.StringVar(value=(chatgpt_bridge.get_saved_api_key() if chatgpt_bridge else ""))
        cg_api_entry = ttk.Entry(chatgpt_frame, show='*', textvariable=cg_api_var, width=56)
        cg_api_entry.grid(row=0, column=1, sticky='ew', pady=6)
        cg_show_var = tk.BooleanVar(value=False)
        def _cg_toggle_show():
            try:
                cg_api_entry.config(show='' if cg_show_var.get() else '*')
            except Exception:
                pass
        ttk.Checkbutton(chatgpt_frame, text="Hien", variable=cg_show_var, command=_cg_toggle_show).grid(row=0, column=2, padx=(6,0))
        ttk.Label(chatgpt_frame, text="OPENAI_MODEL:").grid(row=1, column=0, sticky='w', pady=6)
        cg_model_var = tk.StringVar(value=(chatgpt_bridge.get_saved_model() if chatgpt_bridge else "gpt-4o-mini"))
        ttk.Entry(chatgpt_frame, textvariable=cg_model_var, width=56).grid(row=1, column=1, sticky='ew', pady=6)
        ttk.Label(chatgpt_frame, text="OPENAI_API_BASE:").grid(row=2, column=0, sticky='w', pady=6)
        cg_base_var = tk.StringVar(value=(chatgpt_bridge.get_saved_base() if chatgpt_bridge else "https://api.openai.com"))
        ttk.Entry(chatgpt_frame, textvariable=cg_base_var, width=56).grid(row=2, column=1, sticky='ew', pady=6)
        chatgpt_frame.columnconfigure(1, weight=1)
        def _cg_save():
            if not chatgpt_bridge:
                messagebox.showerror("ChatGPT", "Module chatgpt_bridge chua san sang.")
                return
            key = cg_api_var.get().strip()
            mdl = cg_model_var.get().strip() or "gpt-4o-mini"
            base = cg_base_var.get().strip() or "https://api.openai.com"
            try:
                chatgpt_bridge.set_api_config(key if key else None, model=mdl, base=base)
                ok = chatgpt_bridge.is_configured()
                messagebox.showinfo("ChatGPT", "Da luu cau hinh. " + ("San sang su dung." if ok else "Chua co API Key."))
            except Exception as e:
                messagebox.showerror("ChatGPT", f"Khong the luu: {e}")
        cg_btns = ttk.Frame(chatgpt_frame)
        cg_btns.grid(row=3, column=0, columnspan=3, sticky='e', pady=(12,0))
        ttk.Button(cg_btns, text="Luu ChatGPT", command=_cg_save).pack(side=tk.RIGHT)

        # Gemini tab
        gemini_frame = ttk.Frame(outer if notebook is None else notebook, padding=12)
        ttk.Label(gemini_frame, text="GEMINI_API_KEY:").grid(row=0, column=0, sticky='w', pady=6)
        gm_api_var = tk.StringVar(value=(gemini_bridge.get_saved_api_key() if gemini_bridge else ""))
        gm_api_entry = ttk.Entry(gemini_frame, show='*', textvariable=gm_api_var, width=56)
        gm_api_entry.grid(row=0, column=1, sticky='ew', pady=6)
        gm_show_var = tk.BooleanVar(value=False)
        def _gm_toggle_show():
            try:
                gm_api_entry.config(show='' if gm_show_var.get() else '*')
            except Exception:
                pass
        ttk.Checkbutton(gemini_frame, text="Hien", variable=gm_show_var, command=_gm_toggle_show).grid(row=0, column=2, padx=(6,0))
        gemini_frame.columnconfigure(1, weight=1)
        def _gm_save():
            if not gemini_bridge:
                messagebox.showerror("Gemini", "Module gemini_bridge chua san sang.")
                return
            key = gm_api_var.get().strip()
            try:
                if key:
                    gemini_bridge.set_api_key(key)
                ok = gemini_bridge.is_configured() if gemini_bridge else False
                messagebox.showinfo("Gemini", "Da luu cau hinh. " + ("San sang su dung." if ok else "Chua co API Key."))
            except Exception as e:
                messagebox.showerror("Gemini", f"Khong the luu: {e}")
        gm_btns = ttk.Frame(gemini_frame)
        gm_btns.grid(row=1, column=0, columnspan=3, sticky='e', pady=(12,0))
        ttk.Button(gm_btns, text="Luu Gemini", command=_gm_save).pack(side=tk.RIGHT)

        # Put frames into notebook if available
        # Voice tab
        voice_frame = ttk.Frame(outer if notebook is None else notebook, padding=12)
        ttk.Label(voice_frame, text="Tự động đọc trả lời (TTS):").grid(row=0, column=0, sticky='w', pady=6)
        try:
            auto_tts_var = tk.BooleanVar(value=(voice_mod.get_tts_enabled() if voice_mod else False))
        except Exception:
            auto_tts_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(voice_frame, variable=auto_tts_var).grid(row=0, column=1, sticky='w', pady=6)

        ttk.Label(voice_frame, text="Tốc độ đọc (rate):").grid(row=1, column=0, sticky='w', pady=6)
        try:
            rate_var = tk.IntVar(value=(voice_mod.get_tts_rate() if voice_mod else 170))
        except Exception:
            rate_var = tk.IntVar(value=170)
        rate_scale = ttk.Scale(voice_frame, from_=120, to=220, orient=tk.HORIZONTAL)
        try:
            rate_scale.set(rate_var.get())
        except Exception:
            pass
        rate_scale.grid(row=1, column=1, sticky='ew', pady=6)

        ttk.Label(voice_frame, text="Giọng đọc:").grid(row=2, column=0, sticky='w', pady=6)
        voices = []
        try:
            voices = voice_mod.list_voices() if voice_mod else []
        except Exception:
            voices = []
        voice_names = [name for _, name in voices] if voices else ["Mặc định"]
        voice_ids = [vid for vid, _ in voices] if voices else [None]
        sel_var = tk.StringVar(value=(voice_names[0] if voice_names else "Mặc định"))
        voice_combo = ttk.Combobox(voice_frame, values=voice_names, state='readonly')
        try:
            voice_combo.set(sel_var.get())
        except Exception:
            pass
        voice_combo.grid(row=2, column=1, sticky='ew', pady=6)

        voice_frame.columnconfigure(1, weight=1)

        def _voice_save():
            if not voice_mod:
                messagebox.showerror("TTS", "Thiếu module voice/pyttsx3.")
                return
            try:
                rate_val = int(rate_scale.get())
            except Exception:
                rate_val = 170
            try:
                idx = voice_names.index(voice_combo.get()) if voice_names else -1
            except Exception:
                idx = -1
            vid = voice_ids[idx] if 0 <= idx < len(voice_ids) else None
            try:
                voice_mod.set_voice_config(enabled=bool(auto_tts_var.get()), rate=rate_val, voice_id=vid)
                messagebox.showinfo("TTS", "Đã lưu cài đặt giọng nói.")
            except Exception as e:
                messagebox.showerror("TTS", f"Không thể lưu: {e}")

        vb = ttk.Frame(voice_frame)
        vb.grid(row=3, column=0, columnspan=2, sticky='e', pady=(12,0))
        ttk.Button(vb, text="Lưu giọng nói", command=_voice_save).pack(side=tk.RIGHT)

        if notebook is not None:
            notebook.add(chatgpt_frame, text='ChatGPT')
            notebook.add(gemini_frame, text='Gemini')
            notebook.add(voice_frame, text='Giọng nói')
            notebook.pack(fill=tk.BOTH, expand=True)
        else:
            chatgpt_frame.pack(fill=tk.BOTH, expand=True)
            ttk.Separator(outer, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)
            gemini_frame.pack(fill=tk.BOTH, expand=True)

        bottom = ttk.Frame(outer)
        bottom.pack(fill=tk.X, pady=(12,0))
        ttk.Button(bottom, text="Dong", command=win.destroy).pack(side=tk.RIGHT)

    def open_chatgpt_settings(self):
        if chatgpt_bridge is None:
            messagebox.showerror("ChatGPT", "Module chatgpt_bridge chưa sẵn sàng.")
            return
        win = tk.Toplevel(self.root)
        win.title("Thiết lập ChatGPT")
        win.transient(self.root)
        win.grab_set()

        pal = self.palette_dark if self.dark_mode.get() else self.palette_light
        try:
            win.configure(bg=pal['bg'])
        except Exception:
            pass

        frm = ttk.Frame(win, padding=12)
        frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm, text="API Key:").grid(row=0, column=0, sticky='w', pady=6)
        api_var = tk.StringVar(value=(chatgpt_bridge.get_saved_api_key() if chatgpt_bridge else ""))
        api_entry = ttk.Entry(frm, show='*', textvariable=api_var, width=56)
        api_entry.grid(row=0, column=1, sticky='ew', pady=6)

        show_var = tk.BooleanVar(value=False)
        def toggle_show():
            try:
                api_entry.config(show='' if show_var.get() else '*')
            except Exception:
                pass
        ttk.Checkbutton(frm, text="Hiện", variable=show_var, command=toggle_show).grid(row=0, column=2, padx=(6,0))

        ttk.Label(frm, text="Model:").grid(row=1, column=0, sticky='w', pady=6)
        model_var = tk.StringVar(value=(chatgpt_bridge.get_saved_model() if chatgpt_bridge else "gpt-4o-mini"))
        model_entry = ttk.Entry(frm, textvariable=model_var, width=56)
        model_entry.grid(row=1, column=1, sticky='ew', pady=6)

        ttk.Label(frm, text="API Base:").grid(row=2, column=0, sticky='w', pady=6)
        base_var = tk.StringVar(value=(chatgpt_bridge.get_saved_base() if chatgpt_bridge else "https://api.openai.com"))
        base_entry = ttk.Entry(frm, textvariable=base_var, width=56)
        base_entry.grid(row=2, column=1, sticky='ew', pady=6)

        frm.columnconfigure(1, weight=1)

        def save_and_close():
            key = api_var.get().strip()
            mdl = model_var.get().strip() or "gpt-4o-mini"
            base = base_var.get().strip() or "https://api.openai.com"
            try:
                chatgpt_bridge.set_api_config(key if key else None, model=mdl, base=base)
                ok = chatgpt_bridge.is_configured()
                messagebox.showinfo("ChatGPT", "Đã lưu cấu hình. " + ("Sẵn sàng sử dụng." if ok else "Chưa có API Key."))
                win.destroy()
            except Exception as e:
                messagebox.showerror("ChatGPT", f"Không thể lưu: {e}")

        btns = ttk.Frame(frm)
        btns.grid(row=3, column=0, columnspan=3, sticky='e', pady=(12,0))
        ttk.Button(btns, text="Hủy", command=win.destroy).pack(side=tk.RIGHT, padx=(6,0))
        ttk.Button(btns, text="Lưu", command=save_and_close).pack(side=tk.RIGHT)

    # ========== Placeholder helpers ==========
    def _apply_placeholder(self):
        if not self.input_entry.get():
            self.input_entry.insert(0, self._placeholder_text)
            pal = self.palette_dark if self.dark_mode.get() else self.palette_light
            self.input_entry.configure(foreground=pal['muted'])

    def _on_focus_in(self, _):
        if self.input_entry.get() == self._placeholder_text:
            self.input_entry.delete(0, tk.END)
            pal = self.palette_dark if self.dark_mode.get() else self.palette_light
            self.input_entry.configure(foreground=pal['text'])

    def _on_focus_out(self, _):
        if not self.input_entry.get():
            self._apply_placeholder()

    def _on_history_up(self, event=None):
        if not self.history:
            return 'break'
        if self.history_index == -1:
            self.history_index = len(self.history) - 1
        elif self.history_index > 0:
            self.history_index -= 1
        try:
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, self.history[self.history_index])
        except Exception:
            pass
        return 'break'

    def _on_history_down(self, event=None):
        if not self.history:
            return 'break'
        if self.history_index == -1:
            return 'break'
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            value = self.history[self.history_index]
        else:
            self.history_index = -1
            value = ''
        try:
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, value)
        except Exception:
            pass
        return 'break'

    def _update_char_count(self, event=None):
        try:
            text = self.input_entry.get()
            if text == getattr(self, '_placeholder_text', ''):
                count = 0
            else:
                count = len(text)
            if hasattr(self, 'char_count_label'):
                self.char_count_label.config(text=f"{count} chars")
        except Exception:
            pass

    def clear_chat_action(self):
        if hasattr(self, 'chat'):
            self.chat.clear()

    # ========== App lifecycle ==========
    def on_closing(self):
        get_ai_assistant()._save_data()
        reminder_manager = get_reminder_manager()
        if reminder_manager:
            reminder_manager.save_reminders()
        self.root.destroy()

    def _start_loading_features(self):
        assistant.initialize_assistant()
        self.monitor_feature_loading()
        self.root.after(1000, self._initialize_reminder_notifications)

    def _initialize_reminder_notifications(self):
        reminder_manager = get_reminder_manager()
        if reminder_manager:
            original_send_notification = reminder_manager._send_notification

            def gui_notification(reminder):
                original_send_notification(reminder)
                self.show_reminder_notification(reminder)

            reminder_manager._send_notification = gui_notification

    def show_reminder_notification(self, reminder):
        try:
            title = reminder.get('title') or 'Nhắc nhở'
            description = reminder.get('description') or ''
            when = reminder.get('time')
            time_str = ''
            try:
                if hasattr(when, 'strftime'):
                    time_str = when.strftime('%H:%M %d/%m/%Y')
            except Exception:
                time_str = ''

            msg = f"Đến giờ: {title}"
            if time_str:
                msg += f"\nThời gian: {time_str}"
            if description:
                msg += f"\n\n{description}"

            self.root.after(100, lambda: messagebox.showinfo("Nhắc nhở", msg))
            self._assistant_message(f"(Nhắc nhở) {title}")
        except Exception:
            pass

    # ========== Interaction logic ==========
    def monitor_feature_loading(self):
        if hasattr(assistant, 'basic_features_loaded') and assistant.basic_features_loaded:
            if self.input_entry.cget('state') == 'disabled':
                self.status_label.config(text="Tính năng cơ bản đã sẵn sàng, đang tải thêm…")
                self.input_entry.config(state=tk.NORMAL)
                self.send_button.config(state=tk.NORMAL)
                self.input_entry.focus_set()
                self._assistant_message("Tôi đã sẵn sàng với các tính năng cơ bản. Bạn có thể bắt đầu sử dụng.")

        if hasattr(assistant, 'features_loaded') and assistant.features_loaded.is_set():
            self.status_label.config(text="Tất cả tính năng đã sẵn sàng")
            self.progress.stop()
            self.progress.pack_forget()
            if self.input_entry.cget('state') == 'disabled':
                self.input_entry.config(state=tk.NORMAL)
                self.send_button.config(state=tk.NORMAL)
                self.input_entry.focus_set()
                self._assistant_message("Tôi đã sẵn sàng. Bạn cần giúp gì?")
            total_time = time.time() - self.start_time
            print(f"All features loaded in: {total_time:.2f} seconds")
        else:
            self.root.after(100, self.monitor_feature_loading)

    def process_input(self, event=None):
        user_input = self.input_entry.get().strip()
        if not user_input or user_input == self._placeholder_text:
            return

        # Save to history
        try:
            self.history.append(user_input)
            self.history_index = -1
        except Exception:
            pass

        self._user_message(user_input)
        self.input_entry.delete(0, tk.END)

        self.input_entry.config(state=tk.DISABLED)
        self.send_button.config(state=tk.DISABLED)
        self.processing = True
        self.status_label.config(text="Đang xử lý…")
        try:
            self.progress.pack(side=tk.RIGHT)
            self.progress.start(24)
        except Exception:
            pass
        self._assistant_message("(đang xử lý yêu cầu…)")

        def main_thread_callback(result):
            self.root.after(0, lambda: self._handle_response(result))

        assistant.run_feature_async(user_input, main_thread_callback)

    def _handle_response(self, response):
        try:
            # Remove typing indicator if any
            try:
                if hasattr(self, 'chat'):
                    self.chat.hide_typing_indicator()
            except Exception:
                pass
            self._remove_pending_line()
            self._assistant_message(response)

            self.input_entry.config(state=tk.NORMAL)
            self.send_button.config(state=tk.NORMAL)
            self.processing = False
            self.status_label.config(text="Sẵn sàng")
            try:
                self.progress.stop()
                self.progress.pack_forget()
            except Exception:
                pass
            try:
                if hasattr(self, 'chat'):
                    self.chat.hide_typing_indicator()
            except Exception:
                pass
            self.root.update_idletasks()

            if self.pending_commands:
                next_command = self.pending_commands.pop(0)
                self.input_entry.insert(0, next_command)
                self.process_input()
        except Exception as e:
            print(f"DEBUG: Error in _handle_response: {e}")
            self.processing = False
            self.input_entry.config(state=tk.NORMAL)
            self.send_button.config(state=tk.NORMAL)
            self.status_label.config(text="Sẵn sàng")
            try:
                self.progress.stop()
                self.progress.pack_forget()
            except Exception:
                pass
            self.root.update_idletasks()

    # ========== Output helpers ==========
    def _remove_pending_line(self):
        if hasattr(self, 'chat'):
            self.chat.remove_pending_marker()

    def _add_text(self, text, role='assistant'):
        if hasattr(self, 'chat'):
            self.chat.add_message(role, text)

    def _user_message(self, msg):
        self._add_text(repair_vi(msg), role='user')

    def _assistant_message(self, msg):
        try:
            text = repair_vi(msg)
            tnorm = text.lower()
            if tnorm.startswith('(') and ('dang' in tnorm or 'đang' in tnorm) and ('xu' in tnorm or 'xử' in tnorm or 'ly' in tnorm or 'lý' in tnorm):
                # Treat as typing indicator request, do not add a chat line
                if hasattr(self, 'chat'):
                    self.chat.show_typing_indicator()
                return
        except Exception:
            pass
        try:
            self._last_assistant_text = str(msg)
        except Exception:
            self._last_assistant_text = None
        self._add_text(repair_vi(msg), role='assistant')
        # Auto TTS if enabled
        try:
            if voice_mod and voice_mod.get_tts_enabled():
                import threading
                threading.Thread(target=lambda: voice_mod.speak_text(str(msg)), daemon=True).start()
        except Exception:
            pass

    def _add_quick_button(self, parent, label, command_text):
        def run():
            if self.input_entry.cget('state') != 'disabled':
                self.input_entry.delete(0, tk.END)
                self.input_entry.insert(0, repair_vi(command_text))
                self.process_input()
        ttk.Button(parent, text=repair_vi(label), command=run).pack(fill=tk.X, pady=4)

    def voice_input_action(self):
        """Record from microphone and insert recognized text into input."""
        if voice_mod is None:
            messagebox.showerror("Ghi am (STT)", "Thieu module voice hoac speech_recognition.")
            return
        def _work():
            try:
                txt = voice_mod.transcribe_once(timeout=5.0, phrase_time_limit=12.0, language="vi-VN")
            except Exception:
                txt = None
            def _apply():
                if not txt:
                    messagebox.showerror("Ghi am (STT)", "Khong nhan duoc noi dung.")
                    return
                try:
                    self.input_entry.delete(0, tk.END)
                    self.input_entry.insert(0, txt)
                    self.input_entry.focus_set()
                except Exception:
                    pass
            try:
                self.root.after(0, _apply)
            except Exception:
                _apply()
        try:
            import threading
            threading.Thread(target=_work, daemon=True).start()
        except Exception:
            _work()

    def speak_last_action(self):
        """Speak the last assistant response using TTS."""
        if voice_mod is None:
            messagebox.showerror("Doc TTS", "Thieu module voice hoac pyttsx3.")
            return
        text = getattr(self, '_last_assistant_text', None)
        if not text:
            try:
                if hasattr(self, 'chat') and self.chat.messages:
                    for m in reversed(self.chat.messages):
                        if isinstance(m, tuple) and len(m) >= 3:
                            _, bubble, role = m[:3]
                            if role != 'assistant':
                                continue
                            items = bubble.find_all()
                            if not items:
                                continue
                            tid = items[-1]
                            raw = bubble.itemcget(tid, 'text')
                            text = str(raw)
                            if ': ' in text:
                                text = text.split(': ', 1)[-1]
                            if '\n[' in text:
                                text = text.split('\n[')[0]
                            break
            except Exception:
                text = None
        if not text:
            messagebox.showinfo("Doc TTS", "Chua co phan hoi de doc.")
            return
        def _work_say():
            try:
                voice_mod.speak_text(text)
            except Exception:
                pass
        try:
            import threading
            threading.Thread(target=_work_say, daemon=True).start()
        except Exception:
            _work_say()

def start_gui():
    print("Starting GUI initialization...")
    start_time = time.time()

    root = tk.Tk()
    app = AssistantGUI(root)

    window_time = time.time() - start_time
    print(f"Window created in: {window_time:.2f} seconds")

    def on_window_appear(event=None):
        appear_time = time.time() - start_time
        print(f"Window fully rendered in: {appear_time:.2f} seconds")
        root.unbind('<Map>')

    root.bind('<Map>', on_window_appear)
    root.mainloop()
