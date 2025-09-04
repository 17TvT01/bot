import tkinter as tk
from tkinter import ttk
from typing import Optional

try:
    from .reminder import get_reminder_manager  # type: ignore
except Exception:
    get_reminder_manager = None  # type: ignore


def open_system_info_panel(root: tk.Tk, text: str) -> tk.Toplevel:
    win = tk.Toplevel(root)
    win.title("Thông tin hệ thống")
    win.geometry("640x520")
    frm = ttk.Frame(win, padding=12)
    frm.pack(fill=tk.BOTH, expand=True)
    txt = tk.Text(frm, wrap=tk.WORD)
    txt.pack(fill=tk.BOTH, expand=True)
    try:
        txt.insert(tk.END, str(text))
        txt.configure(state=tk.DISABLED)
    except Exception:
        pass
    return win


def open_clock_panel(root: tk.Tk, initial_text: Optional[str] = None) -> tk.Toplevel:
    import time as _time
    win = tk.Toplevel(root)
    win.title("Đồng hồ")
    win.geometry("320x160")
    frm = ttk.Frame(win, padding=16)
    frm.pack(fill=tk.BOTH, expand=True)
    lbl = ttk.Label(frm, font=("Segoe UI", 28))
    lbl.pack(expand=True)

    def tick():
        try:
            now = _time.strftime("%H:%M:%S")
            lbl.config(text=now)
            win.after(500, tick)
        except Exception:
            pass

    if initial_text:
        try:
            lbl.config(text=str(initial_text))
        except Exception:
            pass
    tick()
    return win


def open_notes_panel(root: tk.Tk) -> tk.Toplevel:
    win = tk.Toplevel(root)
    win.title("Ghi chú / Nhắc nhở")
    win.geometry("720x360")
    frm = ttk.Frame(win, padding=8)
    frm.pack(fill=tk.BOTH, expand=True)
    cols = ("id", "title", "time", "description")
    tree = ttk.Treeview(frm, columns=cols, show="headings")
    for c, t in zip(cols, ["ID", "Tiêu đề", "Thời gian", "Mô tả"]):
        tree.heading(c, text=t)
        tree.column(c, width=120 if c != "description" else 320)
    tree.pack(fill=tk.BOTH, expand=True)

    # Toolbar and actions
    toolbar = ttk.Frame(frm)
    toolbar.pack(fill=tk.X, pady=(6,6))

    def _load_data():
        try:
            for i in tree.get_children():
                tree.delete(i)
            if get_reminder_manager:
                rm = get_reminder_manager()
                for r in getattr(rm, 'reminders', []) or []:
                    rid = str(r.get('id', ''))
                    title = str(r.get('title', ''))
                    t = r.get('time')
                    if hasattr(t, 'strftime'):
                        tstr = t.strftime("%Y-%m-%d %H:%M")
                    else:
                        tstr = str(t)
                    desc = str(r.get('description', ''))
                    tree.insert('', tk.END, values=(rid, title, tstr, desc))
        except Exception:
            pass

    def _delete_selected():
        try:
            if not get_reminder_manager:
                return
            rm = get_reminder_manager()
            sel = tree.selection()
            for item in sel:
                vals = tree.item(item, 'values')
                if vals and len(vals) >= 1:
                    rid = str(vals[0])
                    rm.delete_reminder(rid)
            _load_data()
        except Exception:
            pass

    def _open_add_dialog():
        try:
            if not get_reminder_manager:
                return
            rm = get_reminder_manager()
            w = tk.Toplevel(win)
            w.title("Thêm nhắc nhở")
            w.transient(win)
            try:
                w.grab_set()
            except Exception:
                pass
            f = ttk.Frame(w, padding=12)
            f.pack(fill=tk.BOTH, expand=True)
            ttk.Label(f, text='Tiêu đề').pack(anchor='w')
            e_title = ttk.Entry(f, width=48); e_title.pack(fill=tk.X, pady=(0,8))
            ttk.Label(f, text='Thời gian (vd: 14h ngày mai)').pack(anchor='w')
            e_time = ttk.Entry(f, width=32); e_time.pack(fill=tk.X, pady=(0,8))
            ttk.Label(f, text='Mô tả (tùy chọn)').pack(anchor='w')
            e_desc = ttk.Entry(f, width=64); e_desc.pack(fill=tk.X, pady=(0,12))
            btns = ttk.Frame(f); btns.pack(fill=tk.X)
            def _submit():
                title = e_title.get().strip(); time_str = e_time.get().strip(); desc = e_desc.get().strip()
                if not title or not time_str:
                    try:
                        from tkinter import messagebox as _mb
                        _mb.showerror('Thiếu thông tin', 'Cần nhập Tiêu đề và Thời gian.')
                    except Exception:
                        pass
                    return
                rm.add_reminder(title, time_str, desc)
                try:
                    w.destroy()
                except Exception:
                    pass
                _load_data()
            ttk.Button(btns, text='Thêm', command=_submit).pack(side=tk.RIGHT, padx=4)
            ttk.Button(btns, text='Huỷ', command=lambda: w.destroy()).pack(side=tk.RIGHT)
            try:
                e_title.focus_set()
            except Exception:
                pass
        except Exception:
            pass

    ttk.Button(toolbar, text='Thêm nhắc nhở...', command=_open_add_dialog).pack(side=tk.LEFT)
    ttk.Button(toolbar, text='Xóa mục đã chọn', command=_delete_selected).pack(side=tk.LEFT, padx=6)
    ttk.Button(toolbar, text='Làm mới', command=_load_data).pack(side=tk.LEFT)

    # Context menu for quick delete
    try:
        menu = tk.Menu(tree, tearoff=0)
        menu.add_command(label='Xóa', command=_delete_selected)
        def _popup(ev):
            try:
                iid = tree.identify_row(ev.y)
                if iid:
                    tree.selection_set(iid)
                menu.tk_popup(ev.x_root, ev.y_root)
            finally:
                try:
                    menu.grab_release()
                except Exception:
                    pass
        tree.bind('<Button-3>', _popup)
        tree.bind('<Delete>', lambda e: (_delete_selected(), 'break'))
    except Exception:
        pass

    # Ensure title normalized and data loaded
    try:
        win.title("Ghi chú / Nhắc nhở")
    except Exception:
        pass
    _load_data()

    # Load data
    try:
        if get_reminder_manager:
            rm = get_reminder_manager()
            for r in getattr(rm, 'reminders', []) or []:
                rid = str(r.get('id', ''))
                title = str(r.get('title', ''))
                t = r.get('time')
                if hasattr(t, 'strftime'):
                    tstr = t.strftime("%Y-%m-%d %H:%M")
                else:
                    tstr = str(t)
                desc = str(r.get('description', ''))
                tree.insert('', tk.END, values=(rid, title, tstr, desc))
    except Exception:
        pass
    return win
