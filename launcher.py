#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek Harness Launcher（非官方）
一键启动 DeepSeek Harness 的 Windows 桌面启动器（图形界面版）。

功能：
  1. 单实例运行（重复双击不会启动多个）
  2. 自动检测本机是否已安装 Node.js
  3. 若未安装，自动下载并解压官方便携版 Node.js（无需管理员权限）
  4. 运行 `npx @deepseek-ai/dsh web`
  5. 自动识别 dsh 实际监听地址并打开浏览器

免责声明：本项目与 DeepSeek 官方无任何隶属或关联关系，仅为社区便捷工具。
DeepSeek Harness 的版权与商标归 DeepSeek 所有，遵循其 MIT 开源许可。
"""

import os
import re
import sys
import json
import time
import socket
import shutil
import zipfile
import threading
import urllib.request
import urllib.error
import subprocess
import webbrowser

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

APP_NAME = "DeepSeek Harness Launcher"
DSH_PORT_DEFAULT = 3000
DSH_URL_DEFAULT = f"http://127.0.0.1:{DSH_PORT_DEFAULT}"
NODE_INDEX_URL = "https://nodejs.org/dist/index.json"
NODE_FALLBACK_VERSION = "v20.18.1"
PKG_NAME = "@deepseek-ai/dsh"
SINGLE_INSTANCE_PORT = 39170  # 用于单实例互斥的本地端口

URL_RE = re.compile(r"https?://(127\.0\.0\.1|localhost):(\d+)", re.IGNORECASE)


# -------------------------- 运行环境辅助 --------------------------

def get_base_dir():
    """获取程序所在目录（打包后指向 exe 所在目录）。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_runtime_dir():
    """返回可写的 Node.js 运行时目录；优先放 exe 旁边，不可写则回退到 LOCALAPPDATA。"""
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


def find_npx(node_exe):
    """在 node 同目录或 PATH 中定位 npx 可执行文件。"""
    node_dir = os.path.dirname(node_exe)

    # 1) 同目录下找 npx.cmd / npx / npx-cli.js（标准安装）
    for candidate in ("npx.cmd", "npx", "npx-cli.js"):
        p = os.path.join(node_dir, candidate)
        if os.path.exists(p):
            return p

    # 2) 父目录（有些安装 node 在 bin/ 子目录里）
    parent = os.path.dirname(node_dir.rstrip("/\\"))
    for candidate in ("npx.cmd", "npx", "npx-cli.js"):
        p = os.path.join(parent, candidate)
        if os.path.exists(p):
            return p

    # 3) 系统 PATH 中查找
    system_npx = shutil.which("npx")
    if system_npx:
        return system_npx

    # 4) 通过 node 找到 npm 全局前缀，再从中找 npx
    try:
        prefix = subprocess.check_output(
            [node_exe, "-e", "console.log(require('path').dirname(require('process').execPath))"],
            text=True, timeout=5
        ).strip()
        for sub in ("", "node_modules", "..", "node_modules/npm"):
            for cand in ("npx.cmd", "npx", "bin/npx.cmd"):
                p = os.path.join(prefix, sub, cand)
                if os.path.exists(p):
                    return p
    except Exception:
        pass

    return None


def find_node():
    node = shutil.which("node")
    if node:
        return node
    runtime = os.path.join(get_base_dir(), "runtime", "node", "node.exe")
    if os.path.exists(runtime):
        return runtime
    alt = os.path.join(
        os.environ.get("LOCALAPPDATA", ""),
        "DeepSeekHarnessLauncher", "runtime", "node", "node.exe"
    )
    if os.path.exists(alt):
        return alt
    return None


def get_latest_lts_version():
    try:
        req = urllib.request.Request(
            NODE_INDEX_URL, headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.load(resp)
        for item in data:
            if item.get("lts"):
                return item["version"]
    except Exception as e:
        print("获取在线版本失败：", e)
    return NODE_FALLBACK_VERSION


def acquire_single_instance():
    """通过绑定本地端口实现单实例。返回 socket 表示成功，None 表示已有实例在运行。"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
    try:
        s.bind(("127.0.0.1", SINGLE_INSTANCE_PORT))
        s.listen(1)
        return s
    except OSError:
        return None


# -------------------------- GUI 启动器 --------------------------

class LauncherApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("580x440")
        self.root.resizable(False, False)
        self.proc = None
        self.running = True
        self.server_url = DSH_URL_DEFAULT
        self.lock_socket = None

        ttk.Label(
            root, text="DeepSeek Harness 启动器",
            font=("Microsoft YaHei UI", 16, "bold")
        ).pack(pady=(18, 2))
        ttk.Label(
            root, text="一键启动 DeepSeek 官方智能体框架（非官方社区工具）",
            font=("Microsoft YaHei UI", 9), foreground="#888"
        ).pack(pady=(0, 12))

        self.progress = ttk.Progressbar(
            root, orient="horizontal", length=500, mode="indeterminate"
        )
        self.progress.pack(pady=(0, 10))
        self.progress.start(15)

        self.log = scrolledtext.ScrolledText(
            root, height=15, width=70,
            font=("Consolas", 9), state="disabled",
            bg="#0f1117", fg="#d6e1ff", insertbackground="#d6e1ff"
        )
        self.log.pack(padx=20, pady=(0, 10))

        btn_frame = ttk.Frame(root)
        btn_frame.pack(pady=(0, 14))
        self.open_btn = ttk.Button(
            btn_frame, text="打开浏览器", command=self.open_browser,
            state="disabled"
        )
        self.open_btn.pack(side="left", padx=8)
        ttk.Button(
            btn_frame, text="停止并退出", command=self.stop
        ).pack(side="left", padx=8)

        threading.Thread(target=self.worker, daemon=True).start()
        root.protocol("WM_DELETE_WINDOW", self.stop)

    # ---- 线程安全的 UI 更新 ----
    def append_log(self, msg):
        self.root.after(0, self._append_log, msg)

    def _append_log(self, msg):
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.configure(state="disabled")
        self.log.see("end")

    def set_progress_mode(self, determinate):
        self.root.after(0, self._set_progress_mode, determinate)

    def _set_progress_mode(self, determinate):
        self.progress.stop()
        self.progress.config(mode="determinate" if determinate else "indeterminate")
        if not determinate:
            self.progress.start(15)

    def set_progress(self, value):
        self.root.after(0, self._set_progress, value)

    def _set_progress(self, value):
        self.progress.config(value=value)

    def enable_open(self):
        self.root.after(0, lambda: self.open_btn.configure(state="normal"))

    def open_browser(self):
        webbrowser.open(self.server_url)

    # ---- 主工作流程（后台线程） ----
    def worker(self):
        try:
            self.append_log("正在准备运行环境 ...")
            node = find_node()
            if not node:
                self.append_log("未检测到 Node.js，正在自动安装便携版 ...")
                try:
                    node = self.install_node()
                except Exception as e:
                    self.append_log(f"Node.js 自动安装失败：{e}")
                    self.append_log("请手动安装 Node.js (https://nodejs.org/) 后重试。")
                    self.set_progress_mode(False)
                    return
            else:
                self.append_log(f"已检测到 Node.js：{node}")

            self.append_log("正在启动 DeepSeek Harness（首次会自动下载依赖，请稍候）...")
            self.start_dsh(node)
            self.append_log("等待服务启动 ...")

            if self.wait_for_server(timeout=180):
                self.append_log(f"✅ 服务已就绪：{self.server_url}")
                self.append_log("正在打开浏览器 ...")
                self.enable_open()
                self.open_browser()
            else:
                self.append_log("⚠️ 服务启动较慢，你可手动在浏览器打开：" + self.server_url)
                self.enable_open()
        except Exception as e:
            self.append_log(f"发生错误：{e}")

    def install_node(self):
        version = get_latest_lts_version()
        url = f"https://nodejs.org/dist/{version}/node-{version}-win-x64.zip"
        target_dir = get_runtime_dir()
        zip_path = os.path.join(target_dir, "node.zip")

        self.set_progress_mode(True)
        self.append_log(f"下载 Node.js {version}（约 30MB，请稍候）...")

        def _hook(block_num, block_size, total_size):
            if total_size > 0:
                pct = min(100, int(block_num * block_size * 100 / total_size))
                self.set_progress(pct)
                if block_num % 40 == 0:
                    self.append_log(f"  下载进度：{pct}%")

        urllib.request.urlretrieve(url, zip_path, _hook)
        self.append_log("解压 Node.js ...")
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(target_dir)
        os.remove(zip_path)

        extracted = os.path.join(target_dir, f"node-{version}-win-x64")
        node_exe = os.path.join(extracted, "node.exe")
        if not os.path.exists(node_exe):
            raise FileNotFoundError("Node.js 解压失败，未找到 node.exe")
        self.set_progress_mode(False)
        self.append_log("Node.js 安装完成。")
        return node_exe

    def start_dsh(self, node):
        node_dir = os.path.dirname(node)
        npx = find_npx(node)

        env = os.environ.copy()
        env["PATH"] = node_dir + os.pathsep + env.get("PATH", "")

        if not npx:
            self.append_log("错误：找不到 npx，请确保 Node.js 安装完整。")
            return

        # 判断是 .js 脚本还是 .cmd / 可执行文件
        if npx.endswith(".js"):
            cmd = [node, npx, PKG_NAME, "web"]
        else:
            cmd = [npx, PKG_NAME, "web"]

        self.append_log(f"启动命令：{' '.join(cmd)}")

        self.proc = subprocess.Popen(
            cmd, env=env, cwd=get_base_dir(),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1,
        )

        def _pump():
            for line in self.proc.stdout:
                text = line.rstrip()
                self.append_log(text)
                m = URL_RE.search(text)
                if m and self.server_url == DSH_URL_DEFAULT:
                    self.server_url = m.group(0)
                    self.append_log(f"→ 检测到服务地址：{self.server_url}")

        threading.Thread(target=_pump, daemon=True).start()

    def wait_for_server(self, timeout=180):
        deadline = time.time() + timeout
        while time.time() < deadline and self.running:
            try:
                with urllib.request.urlopen(self.server_url, timeout=2):
                    return True
            except Exception:
                time.sleep(1.5)
        return False

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
    app.lock_socket = lock  # 保持引用，进程退出后系统自动释放端口
    root.mainloop()


if __name__ == "__main__":
    main()
