<h1 align="center">DeepSeek Harness Launcher</h1>

<p align="center">
  <b>一键启动 DeepSeek Harness 的 Windows 桌面应用（非官方）</b><br/>
  下载 → 双击 → 自动打开，无需手动安装 Node.js
</p>

---

## ⚠️ 免责声明

**本项目与 DeepSeek 官方无任何隶属或关联关系**，仅为社区便捷工具。

- [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) 的版权与商标归 **DeepSeek** 所有
- 本项目遵循 DeepSeek Harness 的 **MIT 开源许可**
- "DeepSeek" 为 DeepSeek 公司的注册商标，此处仅为描述性使用

---

## 🚀 三步使用（普通用户）

1. 到 **[Releases](https://github.com/Edgarzwj/DeepSeek-Harness-Launcher/releases)** 页面下载 `DeepSeek-Harness-Launcher.exe`
2. **双击** 打开它
3. 等待浏览器自动弹出 —— 完事！

> 首次运行会自动下载并安装 Node.js（放在程序旁边的 `runtime` 文件夹里，不影响系统），
> 之后再次打开会直接秒启。无需任何命令行操作。

---

## ❓ 这是什么？

[DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness)（dsh）是 **DeepSeek 官方开源的智能体框架（agent harness）**，
采用"一切皆插件"的架构，由 [Cordis](https://github.com/deepseek-ai/cordis) 驱动。

它原本需要用命令行运行：

```bash
npx @deepseek-ai/dsh web
```

**本项目把它包装成了一个真正的 Windows 桌面应用（.exe）**，让不懂命令行的朋友也能一键使用。

---

## ✨ 功能特性

| 特性 | 说明 |
|------|------|
| 图形界面 | 状态日志 + 进度条 + 一键打开浏览器 |
| 自动安装 Node.js | 首次运行自动下载便携版（无需管理员权限） |
| 单实例锁 | 重复双击不会启动多个进程 |
| 端口固定为 3080 | 主动指定官方默认端口并精确打开，不再依赖 dsh 输出格式变化 |
| 运行时目录回退 | exe 旁不可写时自动使用 %LOCALAPPDATA% |

---

## 🛠 开发者：从源码构建

需要本地有 Python 3.10+（含 tkinter）：

```bash
pip install pyinstaller Pillow
pyinstaller --onefile --windowed --icon icon.ico --name "DeepSeek-Harness-Launcher" launcher.py
```

生成的 `dist/DeepSeek-Harness-Launcher.exe` 即为可分发的单文件应用。

---

## 📜 License

MIT
