import time
import threading
from collections import deque
from typing import Optional

try:
    import psutil  # type: ignore
except Exception:  # Graceful fallback when psutil is missing
    psutil = None  # type: ignore

try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
except Exception:
    matplotlib = None  # type: ignore
    FigureCanvasTkAgg = None  # type: ignore
    Figure = None  # type: ignore

import tkinter as tk
from tkinter import ttk, messagebox


class SystemDashboard:
    def __init__(self, root: tk.Tk, interval_ms: int = 1000, history: int = 60):
        self.root = root
        self.interval_ms = max(250, int(interval_ms))
        self.history = max(10, int(history))
        self.win: Optional[tk.Toplevel] = None
        self._after_id = None
        self._lock = threading.RLock()

        # Data buffers
        self.cpu = deque([0.0] * self.history, maxlen=self.history)
        self.mem = deque([0.0] * self.history, maxlen=self.history)
        self.disk_rd = deque([0.0] * self.history, maxlen=self.history)
        self.disk_wr = deque([0.0] * self.history, maxlen=self.history)
        self.net_up = deque([0.0] * self.history, maxlen=self.history)
        self.net_dn = deque([0.0] * self.history, maxlen=self.history)

        self._last_disk = None
        self._last_net = None

    def open(self):
        if matplotlib is None:
            messagebox.showerror("Dashboard", "Thiếu matplotlib. Hãy cài: pip install matplotlib psutil")
            return
        if self.win and tk.Toplevel.winfo_exists(self.win):
            self.win.deiconify()
            self.win.lift()
            return
        self.win = tk.Toplevel(self.root)
        self.win.title("System Dashboard")
        self.win.protocol("WM_DELETE_WINDOW", self._on_close)

        container = ttk.Frame(self.win, padding=8)
        container.pack(fill=tk.BOTH, expand=True)

        self.fig = Figure(figsize=(8, 5), dpi=100)
        self.ax_cpu = self.fig.add_subplot(221)
        self.ax_mem = self.fig.add_subplot(222)
        self.ax_disk = self.fig.add_subplot(223)
        self.ax_net = self.fig.add_subplot(224)

        self.canvas = FigureCanvasTkAgg(self.fig, master=container)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self._draw_static()
        self._schedule()

    def _on_close(self):
        if self._after_id is not None:
            try:
                self.root.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        if self.win and tk.Toplevel.winfo_exists(self.win):
            self.win.destroy()
        self.win = None

    def _draw_static(self):
        for ax in [self.ax_cpu, self.ax_mem, self.ax_disk, self.ax_net]:
            ax.clear()
            ax.grid(True, alpha=0.2)
            ax.set_ylim(0, 100)
        self.ax_cpu.set_title("CPU %")
        self.ax_mem.set_title("Memory %")
        self.ax_disk.set_title("Disk KB/s (R/W)")
        self.ax_net.set_title("Network KB/s (Up/Down)")
        self.canvas.draw_idle()

    def _schedule(self):
        self._update_data()
        self._redraw()
        self._after_id = self.root.after(self.interval_ms, self._schedule)

    def _update_data(self):
        with self._lock:
            # CPU & Memory
            if psutil:
                try:
                    c = float(psutil.cpu_percent(interval=None))
                except Exception:
                    c = 0.0
                try:
                    m = float(psutil.virtual_memory().percent)
                except Exception:
                    m = 0.0
            else:
                c = m = 0.0
            self.cpu.append(c)
            self.mem.append(m)

            # Disk
            if psutil:
                try:
                    now = psutil.disk_io_counters()
                    if self._last_disk:
                        dt = max(self.interval_ms / 1000.0, 0.001)
                        rd = max(0.0, (now.read_bytes - self._last_disk.read_bytes) / 1024.0 / dt)
                        wr = max(0.0, (now.write_bytes - self._last_disk.write_bytes) / 1024.0 / dt)
                    else:
                        rd = wr = 0.0
                    self._last_disk = now
                except Exception:
                    rd = wr = 0.0
            else:
                rd = wr = 0.0
            self.disk_rd.append(rd)
            self.disk_wr.append(wr)

            # Network
            if psutil:
                try:
                    now = psutil.net_io_counters()
                    if self._last_net:
                        dt = max(self.interval_ms / 1000.0, 0.001)
                        up = max(0.0, (now.bytes_sent - self._last_net.bytes_sent) / 1024.0 / dt)
                        dn = max(0.0, (now.bytes_recv - self._last_net.bytes_recv) / 1024.0 / dt)
                    else:
                        up = dn = 0.0
                    self._last_net = now
                except Exception:
                    up = dn = 0.0
            else:
                up = dn = 0.0
            self.net_up.append(up)
            self.net_dn.append(dn)

    def _redraw(self):
        with self._lock:
            x = range(len(self.cpu))
            # CPU
            self.ax_cpu.clear(); self.ax_cpu.grid(True, alpha=0.2); self.ax_cpu.set_ylim(0, 100); self.ax_cpu.set_title("CPU %")
            self.ax_cpu.plot(x, list(self.cpu), color="#58A6FF")
            self.ax_cpu.text(0.02, 0.9, f"{self.cpu[-1]:.1f}%", transform=self.ax_cpu.transAxes)
            # Memory
            self.ax_mem.clear(); self.ax_mem.grid(True, alpha=0.2); self.ax_mem.set_ylim(0, 100); self.ax_mem.set_title("Memory %")
            self.ax_mem.plot(x, list(self.mem), color="#3FB950")
            self.ax_mem.text(0.02, 0.9, f"{self.mem[-1]:.1f}%", transform=self.ax_mem.transAxes)
            # Disk
            self.ax_disk.clear(); self.ax_disk.grid(True, alpha=0.2); self.ax_disk.set_ylim(bottom=0)
            self.ax_disk.plot(x, list(self.disk_rd), color="#F78166", label="Read")
            self.ax_disk.plot(x, list(self.disk_wr), color="#DB61A2", label="Write")
            self.ax_disk.legend(loc="upper left"); self.ax_disk.set_title("Disk KB/s (R/W)")
            # Network
            self.ax_net.clear(); self.ax_net.grid(True, alpha=0.2); self.ax_net.set_ylim(bottom=0)
            self.ax_net.plot(x, list(self.net_up), color="#F2CC60", label="Up")
            self.ax_net.plot(x, list(self.net_dn), color="#8B949E", label="Down")
            self.ax_net.legend(loc="upper left"); self.ax_net.set_title("Network KB/s (Up/Down)")
            self.canvas.draw_idle()


def open_dashboard(root: tk.Tk) -> SystemDashboard:
    dash = SystemDashboard(root)
    dash.open()
    return dash

