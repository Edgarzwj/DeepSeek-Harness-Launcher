#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek Harness Launcher（非官方）
双击即可启动 DeepSeek Harness 并打开其网页界面。

特性：
  - 启动前清理残留的 dsh 进程（避免端口被占用）
  - 自动探测 dsh 实际监听端口
  - 自动打开浏览器到正确地址
  - 极简界面：状态 + 打开浏览器 + 退出

免责声明：本项目与 DeepSeek 官方无任何隶属或关联关系，仅为社区便捷工具。
DeepSeek Harness 遵循其 MIT 开源许可，"DeepSeek" 为 DeepSeek 公司商标，此处为描述性使用。
"""

import os
import re
import sys
import json
import time
import socket
import shutil
import subprocess
import urllib.request
import urllib.error
import threading
import webbrowser

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

APP_NAME = "DeepSeek Harness Launcher"
NODE_INDEX_URL = "https://nodejs.org/dist/index.json"
NODE_FALLBACK_VERSION = "v20.18.1"
PKG_NAME = "@deepseek-ai/dsh"
SINGLE_INSTANCE_PORT = 39170
# 与官方 DeepSeek Harness web 默认端口保持一致（参考文档：serves http://127.0.0.1:3080 by default）。
# 主动指定该端口，启动器即可精确打开，无需依赖官方输出格式或被动扫描端口。
DSH_PORT = 3080
DSH_PORT_SCAN_RANGE = range(3000, 3300)  # 兜底扫描范围，覆盖 3080 及周边

# 匹配 dsh 输出中的监听地址（如 http://localhost:3080 或 http://127.0.0.1:3080）
URL_RE = re.compile(r"https?://[a-zA-Z0-9.\-]+:(\d+)", re.IGNORECASE)
# 只记录"有用"的日志行，避免刷屏
INTERESTING = ("error", "fail", "exception", "cannot", "refused",
               "local:", "http://", "https://", "ready", "started",
               "listening", "3080", "3000", "open")


# -------------------------- 环境辅助 --------------------------

def get_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_runtime_dir():
    primary = os.path.join(get_base_dir(), "runtime", "node")
    try:
        os.makedirs(primary, exist_ok=True)
        test = os.path.join(primary, ".writetest")
        with open(test, "w") as f:
            f.write("1")
        os.remove(test)
        return primary
    except Exception:
        alt = os.path.join(
            os.environ.get("LOCALAPPDATA", get_base_dir()),
            "DeepSeekHarnessLauncher", "runtime", "node"
        )
        os.makedirs(alt, exist_ok=True)
        return alt


def find_node():
    node = shutil.which("node")
    if node:
        return node
    for base in (get_base_dir(),
                 os.path.join(os.environ.get("LOCALAPPDATA", ""), "DeepSeekHarnessLauncher", "runtime", "node")):
        cand = os.path.join(base, "runtime", "node", "node.exe")
        if os.path.exists(cand):
            return cand
    # 常见安装位置
    for path in (r"D:\node.js\node.exe", r"C:\nodejs\node.exe",
                 r"C:\Program Files\nodejs\node.exe"):
        if os.path.exists(path):
            return path
    return None


def find_npx(node_exe):
    node_dir = os.path.dirname(node_exe)
    for candidate in ("npx.cmd", "npx", "npx-cli.js"):
        p = os.path.join(node_dir, candidate)
        if os.path.exists(p):
            return p
    parent = os.path.dirname(node_dir.rstrip("/\\"))
    for candidate in ("npx.cmd", "npx", "npx-cli.js"):
        p = os.path.join(parent, candidate)
        if os.path.exists(p):
            return p
    system_npx = shutil.which("npx")
    if system_npx:
        return system_npx
    return None


def get_latest_lts_version():
    try:
        req = urllib.request.Request(NODE_INDEX_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.load(resp)
        for item in data:
            if item.get("lts"):
                return item["version"]
    except Exception:
        pass
    return NODE_FALLBACK_VERSION


def acquire_single_instance():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", SINGLE_INSTANCE_PORT))
        s.listen(1)
        return s
    except OSError:
        return None


def kill_existing_dsh():
    """启动前清理残留的 dsh 进程，避免端口被占用（EADDRINUSE）。"""
    killed = []
    try:
        out = subprocess.check_output(
            ["wmic", "process", "where", "name='node.exe'",
             "get", "processid,commandline", "/format:csv"],
            text=True, stderr=subprocess.DEVNULL, timeout=15
        )
        for line in out.splitlines():
            if "@deepseek-ai/dsh" in line or "dsh-host" in line or "dsh-app-boot" in line:
                pid = line.split(",")[-1].strip()
                if pid.isdigit() and pid != str(os.getpid()):
                    try:
                        subprocess.run(["taskkill", "/F", "/PID", pid],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
                        killed.append(pid)
                    except Exception:
                        pass
    except Exception:
        pass
    return killed


# -------------------------- GUI --------------------------

class LauncherApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("460x260")
        self.root.resizable(False, False)
        self.proc = None
        self.running = True
        self.server_url = None
        self.lock_socket = None

        ttk.Label(root, text="DeepSeek Harness 启动器",
                  font=("Microsoft YaHei UI", 15, "bold")).pack(pady=(16, 2))
        ttk.Label(root, text="双击即可启动 DeepSeek 智能体框架（非官方）",
                  font=("Microsoft YaHei UI", 9), foreground="#888").pack(pady=(0, 10))

        self.status = ttk.Label(root, text="正在准备运行环境 ...",
                                font=("Microsoft YaHei UI", 11), foreground="#333")
        self.status.pack(pady=(4, 6))

        self.progress = ttk.Progressbar(root, orient="horizontal",
                                        length=400, mode="indeterminate")
        self.progress.pack(pady=(0, 10))
        self.progress.start(15)

        self.detail = scrolledtext.ScrolledText(
            root, height=4, width=56, font=("Consolas", 8),
            state="disabled", bg="#0f1117", fg="#9fb3ff"
        )
        self.detail.pack(padx=16, pady=(0, 8))

        btn_frame = ttk.Frame(root)
        btn_frame.pack(pady=(0, 10))
        self.open_btn = ttk.Button(btn_frame, text="打开浏览器",
                                   command=self.open_browser, state="disabled")
        self.open_btn.pack(side="left", padx=10)
        ttk.Button(btn_frame, text="退出", command=self.stop).pack(side="left", padx=10)

        threading.Thread(target=self.worker, daemon=True).start()
        root.protocol("WM_DELETE_WINDOW", self.stop)

    # ---- UI 更新 ----
    def set_status(self, text, color="#333"):
        self.root.after(0, lambda: (self.status.config(text=text, foreground=color)))

    def log(self, msg):
        self.root.after(0, self._log, msg)

    def _log(self, msg):
        self.detail.configure(state="normal")
        self.detail.insert("end", msg + "\n")
        self.detail.configure(state="disabled")
        self.detail.see("end")

    def log_if_interesting(self, text):
        low = text.lower()
        if any(k in low for k in INTERESTING):
            self.log(text)

    def enable_open(self):
        self.root.after(0, lambda: self.open_btn.configure(state="normal"))

    def open_browser(self):
        if self.server_url:
            webbrowser.open(self.server_url)

    # ---- 工作流 ----
    def worker(self):
        try:
            # 1. 清理残留进程
            killed = kill_existing_dsh()
            if killed:
                self.log(f"已清理 {len(killed)} 个残留进程")

            # 2. 确保 Node.js
            self.set_status("正在检查 Node.js ...")
            node = find_node()
            if not node:
                self.set_status("正在安装 Node.js（首次，请稍候）...")
                try:
                    node = self.install_node()
                except Exception as e:
                    self.set_status("❌ Node.js 安装失败", "#c0392b")
                    self.log(f"错误：{e}")
                    self.log("请手动安装 Node.js: https://nodejs.org/")
                    return
            self.log(f"Node.js: {node}")

            # 3. 启动 dsh
            self.set_status("正在启动 DeepSeek Harness ...（首次会下载并初始化，请稍候）")
            self.start_dsh(node)

            # 4. 探测端口并打开浏览器（首次初始化/下载可能较慢，放宽超时）
            url = self.wait_for_url(timeout=420)
            if url:
                self.server_url = url
                self.set_status(f"✅ 已启动：{url}", "#1a8a3c")
                self.enable_open()
                self.log("正在打开浏览器 ...")
                webbrowser.open(url)
            else:
                self.set_status("⚠️ 启动较慢，请点“打开浏览器”或查看日志", "#b8860b")
                self.enable_open()
        except Exception as e:
            self.set_status("❌ 启动失败", "#c0392b")
            self.log(f"错误：{e}")

    def install_node(self):
        version = get_latest_lts_version()
        url = f"https://nodejs.org/dist/{version}/node-{version}-win-x64.zip"
        target_dir = get_runtime_dir()
        zip_path = os.path.join(target_dir, "node.zip")
        self.log(f"下载 Node.js {version}（约 30MB）...")
        urllib.request.urlretrieve(url, zip_path)
        self.log("解压 Node.js ...")
        import zipfile
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(target_dir)
        os.remove(zip_path)
        node_exe = os.path.join(target_dir, f"node-{version}-win-x64", "node.exe")
        if not os.path.exists(node_exe):
            raise FileNotFoundError("Node.js 解压失败")
        self.log("Node.js 安装完成。")
        return node_exe

    def start_dsh(self, node):
        npx = find_npx(node)
        if not npx:
            raise RuntimeError("找不到 npx，请确认 Node.js 安装完整")
        node_dir = os.path.dirname(node)
        env = os.environ.copy()
        env["PATH"] = node_dir + os.pathsep + env.get("PATH", "")
        # 主动指定端口（与官方默认一致），并用 --no-open 关闭官方自带浏览器打开，
        # 改由本启动器统一打开，避免双重弹窗以及「官方输出格式变化导致检测不到地址」的问题。
        dsh_args = [PKG_NAME, "web", "--no-open", "--port", str(DSH_PORT)]
        cmd = [node, npx] + dsh_args if npx.endswith(".js") else [npx] + dsh_args
        self.log(f"命令：{' '.join(cmd)}")

        self.proc = subprocess.Popen(
            cmd, env=env, cwd=get_base_dir(),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1
        )

        def _pump():
            for line in self.proc.stdout:
                text = line.rstrip()
                self.log_if_interesting(text)
                m = URL_RE.search(text)
                if m and not self.server_url:
                    port = m.group(1)
                    self.server_url = f"http://127.0.0.1:{port}"
                    self.log(f"→ 检测到地址：{self.server_url}")

        threading.Thread(target=_pump, daemon=True).start()

    def wait_for_url(self, timeout=420):
        deadline = time.time() + timeout
        # 已知端口优先（已由 --port 显式指定），无需依赖 stdout 解析或端口扫描
        candidates = []
        if self.server_url:
            candidates.append(self.server_url)
        candidates.append(f"http://127.0.0.1:{DSH_PORT}")
        while time.time() < deadline and self.running:
            for url in candidates:
                try:
                    urllib.request.urlopen(url, timeout=1.5)
                    return url
                except Exception:
                    pass
            # 兜底：扫描端口范围，兼容旧版或自定义端口
            for port in DSH_PORT_SCAN_RANGE:
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}", timeout=0.4):
                        return f"http://127.0.0.1:{port}"
                except Exception:
                    continue
            time.sleep(1.5)
        # 即便超时未连上，也返回已知地址，便于用户手动打开
        return self.server_url or f"http://127.0.0.1:{DSH_PORT}"

    def stop(self):
        self.running = False
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except Exception:
                self.proc.kill()
        self.root.destroy()


def main():
    lock = acquire_single_instance()
    if lock is None:
        root = tk.Tk()
        root.withdraw()
        messagebox.showwarning(APP_NAME, "DeepSeek Harness Launcher 已在运行中。")
        root.destroy()
        return
    root = tk.Tk()
    app = LauncherApp(root)
    app.lock_socket = lock
    root.mainloop()


if __name__ == "__main__":
    main()
