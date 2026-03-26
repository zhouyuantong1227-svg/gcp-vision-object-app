from __future__ import annotations

import os
import socket
import sys
import threading
import traceback
import urllib.request
import webbrowser
from datetime import datetime
from pathlib import Path
from tkinter import BooleanVar, StringVar, Tk, ttk, messagebox

import uvicorn

from app.main import app

if getattr(sys, "frozen", False):
    ROOT_DIR = Path(sys.executable).resolve().parent
else:
    ROOT_DIR = Path(__file__).resolve().parent

ENV_FILE = ROOT_DIR / ".env.local"
LOG_FILE = ROOT_DIR / "launcher.log"
DEFAULT_PORT = 8000
POLL_INTERVAL_MS = 500
STARTUP_TIMEOUT_MS = 20000


def write_log(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        LOG_FILE.write_text("", encoding="utf-8") if not LOG_FILE.exists() else None
        with LOG_FILE.open("a", encoding="utf-8") as handle:
            handle.write(f"[{timestamp}] {message}\n")
    except Exception:
        pass


def load_env_file() -> dict[str, str]:
    if not ENV_FILE.exists():
        return {}

    values: dict[str, str] = {}
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def save_env_file(api_key: str) -> None:
    ENV_FILE.write_text(f"VISION_API_KEY={api_key}\n", encoding="utf-8")


def find_available_port(start_port: int = DEFAULT_PORT) -> int:
    for port in range(start_port, start_port + 30):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError("No available local port found.")


class LauncherWindow:
    def __init__(self) -> None:
        saved_key = load_env_file().get("VISION_API_KEY", "")
        self.root = Tk()
        self.root.title("Vision App Launcher")
        self.root.geometry("620x420")
        self.root.minsize(620, 420)
        self.root.configure(bg="#f5efe5")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.report_callback_exception = self.report_callback_exception

        self.api_key_var = StringVar(value=saved_key)
        self.save_key_var = BooleanVar(value=bool(saved_key))
        self.status_var = StringVar(value="请输入 Cloud Vision API Key，然后点击“启动应用”。")
        self.url_var = StringVar(value="应用地址：尚未启动")
        self.server: uvicorn.Server | None = None
        self.server_thread: threading.Thread | None = None
        self.base_url = ""
        self.startup_elapsed_ms = 0

        self._build_ui()
        write_log(f"launcher_started frozen={getattr(sys, 'frozen', False)} root={ROOT_DIR}")

    def _build_ui(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Panel.TFrame", background="#fff9f1")
        style.configure(
            "Hero.TLabel",
            background="#f5efe5",
            foreground="#1f1a16",
            font=("Microsoft YaHei UI", 26, "bold"),
        )
        style.configure(
            "Body.TLabel",
            background="#f5efe5",
            foreground="#6f6255",
            font=("Microsoft YaHei UI", 11),
        )
        style.configure(
            "PanelTitle.TLabel",
            background="#fff9f1",
            foreground="#1f1a16",
            font=("Microsoft YaHei UI", 13, "bold"),
        )
        style.configure(
            "PanelText.TLabel",
            background="#fff9f1",
            foreground="#6f6255",
            font=("Microsoft YaHei UI", 10),
        )
        style.configure("Primary.TButton", font=("Microsoft YaHei UI", 11, "bold"))

        container = ttk.Frame(self.root, padding=24)
        container.pack(fill="both", expand=True)

        ttk.Label(container, text="云端图片目标识别启动器", style="Hero.TLabel").pack(anchor="w")
        ttk.Label(
            container,
            text="输入 Cloud Vision API Key 后启动本地服务，并自动打开识别网页。",
            style="Body.TLabel",
            wraplength=560,
        ).pack(anchor="w", pady=(8, 18))

        panel = ttk.Frame(container, style="Panel.TFrame", padding=20)
        panel.pack(fill="both", expand=True)

        ttk.Label(panel, text="Vision API Key", style="PanelTitle.TLabel").pack(anchor="w")
        ttk.Entry(panel, textvariable=self.api_key_var, font=("Consolas", 11), width=64, show="*").pack(
            fill="x", pady=(10, 8)
        )
        ttk.Checkbutton(panel, text="记住密钥，下次自动填充", variable=self.save_key_var).pack(anchor="w")

        ttk.Label(
            panel,
            text="关闭这个窗口时，本地识别服务也会退出。",
            style="PanelText.TLabel",
            wraplength=520,
        ).pack(anchor="w", pady=(14, 10))

        button_row = ttk.Frame(panel, style="Panel.TFrame")
        button_row.pack(fill="x", pady=(8, 10))

        self.start_button = ttk.Button(button_row, text="启动应用", style="Primary.TButton", command=self.start_app)
        self.start_button.pack(side="left")

        self.open_button = ttk.Button(button_row, text="打开识别页面", command=self.open_browser)
        self.open_button.pack(side="left", padx=10)
        self.open_button.state(["disabled"])

        ttk.Button(button_row, text="退出", command=self.on_close).pack(side="right")

        ttk.Label(panel, textvariable=self.status_var, style="PanelText.TLabel", wraplength=520).pack(
            anchor="w", pady=(14, 6)
        )
        ttk.Label(panel, textvariable=self.url_var, style="PanelText.TLabel").pack(anchor="w")

    def report_callback_exception(self, exc_type, exc_value, exc_traceback) -> None:  # noqa: ANN001
        detail = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        write_log(detail)
        messagebox.showerror("启动器错误", f"{exc_value}\n\n日志文件：{LOG_FILE}")

    def set_status(self, message: str) -> None:
        self.status_var.set(message)
        write_log(f"status={message}")

    def start_app(self) -> None:
        api_key = self.api_key_var.get().strip()
        if not api_key:
            messagebox.showerror("缺少密钥", "请输入 Cloud Vision API Key。")
            return

        os.environ["PYTHONUTF8"] = "1"
        os.environ["VISION_API_KEY"] = api_key

        if self.save_key_var.get():
            save_env_file(api_key)
        elif ENV_FILE.exists():
            ENV_FILE.unlink()

        if self.server_thread and self.server_thread.is_alive():
            self.set_status("本地服务已经在运行，正在打开识别页面。")
            self.open_browser()
            return

        port = find_available_port(DEFAULT_PORT)
        self.base_url = f"http://127.0.0.1:{port}"
        self.url_var.set(f"应用地址：{self.base_url}")
        self.set_status("正在启动本地服务，请稍候...")
        self.start_button.state(["disabled"])
        self.open_button.state(["disabled"])
        self.startup_elapsed_ms = 0

        config = uvicorn.Config(
            app,
            host="127.0.0.1",
            port=port,
            log_level="warning",
            log_config=None,
            access_log=False,
        )
        self.server = uvicorn.Server(config)
        self.server_thread = threading.Thread(target=self.run_server, daemon=True)
        self.server_thread.start()

        self.root.after(POLL_INTERVAL_MS, self.poll_server_startup)

    def run_server(self) -> None:
        try:
            write_log("server_thread_started")
            if self.server is not None:
                self.server.run()
            write_log("server_thread_exited")
        except Exception:
            write_log(traceback.format_exc())

    def poll_server_startup(self) -> None:
        if self.server_thread is None:
            return

        if not self.server_thread.is_alive():
            self.server = None
            self.server_thread = None
            self.set_status("服务启动失败。请检查 launcher.log。")
            self.start_button.state(["!disabled"])
            messagebox.showerror("启动失败", f"本地服务未能成功启动。\n日志文件：{LOG_FILE}")
            return

        try:
            with urllib.request.urlopen(f"{self.base_url}/healthz", timeout=1.5) as response:
                if response.status == 200:
                    self._on_server_ready()
                    return
        except Exception:
            pass

        self.startup_elapsed_ms += POLL_INTERVAL_MS
        if self.startup_elapsed_ms >= STARTUP_TIMEOUT_MS:
            self.stop_server()
            self.set_status("服务启动超时。请检查 launcher.log。")
            self.start_button.state(["!disabled"])
            messagebox.showerror("启动超时", f"本地服务启动超时。\n日志文件：{LOG_FILE}")
            return

        self.root.after(POLL_INTERVAL_MS, self.poll_server_startup)

    def _on_server_ready(self) -> None:
        self.set_status("服务已启动，浏览器即将打开识别页面。")
        self.open_button.state(["!disabled"])
        webbrowser.open(self.base_url)

    def open_browser(self) -> None:
        if self.base_url:
            webbrowser.open(self.base_url)

    def stop_server(self) -> None:
        if self.server is not None:
            self.server.should_exit = True
        self.server = None
        self.server_thread = None
        write_log("server_stop_requested")

    def on_close(self) -> None:
        self.stop_server()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    LauncherWindow().run()
