<h1 align="center">DeepSeek Harness Launcher</h1>

<p align="center">
  <b>一键启动 DeepSeek Harness 的 Windows 桌面应用</b><br/>
  下载 → 双击 → 自动打开，无需手动安装 Node.js
</p>

---

## 🚀 三步使用（普通用户）

1. 到 **[Releases](https://github.com/Edgarzwj/DeepSeek-Harness-Launcher/releases)** 页面下载 `DeepSeek-Harness-Launcher.exe`
2. **双击** 打开它
3. 等待浏览器自动弹出 `http://127.0.0.1:3000` —— 完事！

> 首次运行会自动下载并安装 Node.js（放在程序旁边的 `runtime` 文件夹里，不影响系统），
> 之后再次打开会直接秒启。无需任何命令行操作。

---

## ❓ 这是什么？

[DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness)（dsh）是 DeepSeek 官方开源的 **智能体框架（agent harness）**，
采用"一切皆插件"的架构，由 [Cordis](https://github.com/deepseek-ai/cordis) 驱动。

它原本需要用命令行运行：

```bash
npx @deepseek-ai/dsh web
```

**本项目把它包装成了一个真正的 Windows 桌面应用（.exe）**，让不懂命令行的朋友也能一键使用。

---

## 🧩 技术说明

| 项目 | 说明 |
|------|------|
| 启动方式 | 双击 `DeepSeek-Harness-Launcher.exe` |
| Node.js | 首次运行自动下载便携版（无需管理员权限，不污染系统） |
| 实际命令 | `npx @deepseek-ai/dsh web` |
| 默认地址 | `http://127.0.0.1:3000` |
| 关闭方式 | 关闭启动器窗口即可停止服务 |

---

## 🛠 开发者：从源码构建

需要本地有 Python 3.10+：

```bash
pip install pyinstaller
pyinstaller --onefile --name "DeepSeek-Harness-Launcher" launcher.py
```

生成的 `dist/DeepSeek-Harness-Launcher.exe` 即为可分发的单文件应用。

---

## 📜 License

MIT
