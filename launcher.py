#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek Harness Launcher
一键启动 DeepSeek Harness 的 Windows 桌面启动器（图形界面版）。

功能：
  1. 自动检测本机是否已安装 Node.js
  2. 若未安装，自动下载并解压官方便携版 Node.js（无需管理员权限）
  3. 运行 `npx @deepseek-ai/dsh web`
  4. 服务就绪后自动打开默认浏览器
"""

import os
import sys
import json
import time
import shutil
import zipfile
import threading
import urllib.request
import urllib.error
import subprocess
import webbrowser

import tkinter as tk
from tkinter import ttk, scrolledtext

APP_NAME = "DeepSeek Harness Launcher"
DSH_PORT = 3000
DSH_URL = f"http://127.0.0.1:{DSH_PORT}"
NODE_INDEX_URL = "https://nodejs.org/dist/index.json"
NODE_FALLBACK_VERSION = "v20.18.1"
PKG_NAME = "@deepseek-ai/dsh"


# -------------------------- 运行环境辅助 --------------------------

def get_base_dir():
    """获取程序所在目录（打包后指向 exe 所在目录）。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def find_node():
    node = shutil.which("node")
    if node:
        return node
    runtime = os.path.join(get_base_dir(), "runtime", "node", "node.exe")
    if os.path.exists(runtime):
        return runtime
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


# -------------------------- GUI 启动器 --------------------------

class LauncherApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("560x420")
        self.root.resizable(False, False)
        self.proc = None
        self.running = True

        # 标题
        ttk.Label(
            root, text="DeepSeek Harness 启动器",
            font=("Microsoft YaHei UI", 16, "bold")
        ).pack(pady=(18, 4))
        ttk.Label(
            root, text="一键启动 DeepSeek 官方智能体框架",
            font=("Microsoft YaHei UI", 10), foreground="#666"
        ).pack(pady=(0, 12))

        # 进度条
        self.progress = ttk.Progressbar(
            root, orient="horizontal", length=480, mode="indeterminate"
        )
        self.progress.pack(pady=(0, 10))
        self.progress.start(15)

        # 状态日志框
        self.log = scrolledtext.ScrolledText(
            root, height=14, width=68,
            font=("Consolas", 9), state="disabled",
            bg="#0f1117", fg="#d6e1ff", insertbackground="#d6e1ff"
        )
        self.log.pack(padx=20, pady=(0, 10))

        # 底部按钮
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

        # 启动工作线程
        threading.Thread(target=self.worker, daemon=True).start()

        root.protocol("WM_DELETE_WINDOW", self.stop)

    # ---- 线程安全的日志 ----
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

    def open_browser(self):
        webbrowser.open(DSH_URL)

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
            if self.wait_for_server(DSH_URL, timeout=180):
                self.append_log(f"✅ 服务已就绪：{DSH_URL}")
                self.append_log("正在打开浏览器 ...")
                self.root.after(0, lambda: self.open_btn.configure(state="normal"))
                self.open_browser()
            else:
                self.append_log("⚠️ 服务启动较慢，你可手动在浏览器打开：" + DSH_URL)
                self.root.after(0, lambda: self.open_btn.configure(state="normal"))
        except Exception as e:
            self.append_log(f"发生错误：{e}")

    def install_node(self):
        version = get_latest_lts_version()
        url = f"https://nodejs.org/dist/{version}/node-{version}-win-x64.zip"
        target_dir = os.path.join(get_base_dir(), "runtime", "node")
        os.makedirs(target_dir, exist_ok=True)
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
        npx_cli = os.path.join(node_dir, "npx-cli.js")

        env = os.environ.copy()
        env["PATH"] = node_dir + os.pathsep + env.get("PATH", "")

        if os.path.exists(npx_cli):
            cmd = [node, npx_cli, PKG_NAME, "web"]
        else:
            cmd = ["npx", PKG_NAME, "web"]

        self.proc = subprocess.Popen(
            cmd, env=env, cwd=get_base_dir(),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1,
        )

        def _pump():
            for line in self.proc.stdout:
                self.append_log(line.rstrip())

        threading.Thread(target=_pump, daemon=True).start()

    def wait_for_server(self, url, timeout=180):
        deadline = time.time() + timeout
        while time.time() < deadline and self.running:
            try:
                with urllib.request.urlopen(url, timeout=2):
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
    root = tk.Tk()
    LauncherApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
