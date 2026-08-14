# DSH Launcher

> **DeepSeek Harness** 一键启动器 —— 下载即用，无需记命令

让任何人都能双击启动 DeepSeek Harness，不用折腾 Node.js 命令行。

## ✨ 特性

- 🪟 Windows 双击 `dsh.bat` 即可运行
- 🍎 Mac / Linux 终端运行 `./dsh.sh`
- 🔍 自动检测 Node.js 环境，缺失时给出安装指引
- 🚀 首次运行自动通过 npx 下载依赖

## 🚀 快速开始

### Windows 用户

1. **安装 [Node.js LTS](https://nodejs.org/)**（如果还没装）
2. 双击 `dsh.bat`
3. 浏览器自动打开 `http://127.0.0.1:3000`

### Mac / Linux 用户

1. **安装 Node.js**（如果还没装）
   - macOS: `brew install node`
   - Linux: 参考 https://nodejs.org/
2. 终端执行：
   ```bash
   chmod +x dsh.sh
   ./dsh.sh
   ```
3. 浏览器自动打开 `http://127.0.0.1:3000`

## 📖 DeepSeek Harness 是什么？

DeepSeek Harness（dsh）是 [DeepSeek AI](https://github.com/deepseek-ai) 开发的开源 **agent harness（智能体框架）**。

它采用一切皆插件的架构，由 [Cordis](https://github.com/deepseek-ai/cordis) 驱动。

📄 官方文档：https://github.com/deepseek-ai/deepseek-harness

## ⚠️ 注意事项

- 首次运行需要联网下载包（约几十 MB），之后会有缓存
- 默认端口为 `3000`，如被占用可手动运行 `npx @deepseek-ai/dsh web --port <端口号>`
- 需要 Node.js >= 18

## 📜 License

MIT

---

**启动器本身零依赖，仅调用官方 `npx @deepseek-ai/dsh web` 命令。**
