#!/bin/bash

echo ""
echo "  ╔════════════════════════════════════════╗"
echo "  ║     DeepSeek Harness - Quick Launch    ║"
echo "  ╚════════════════════════════════════════╝"
echo ""

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "  [✗] Node.js 未检测到"
    echo ""
    echo "  请先安装 Node.js:"
    echo "  macOS: brew install node"
    echo "  Linux: 请访问 https://nodejs.org/"
    echo ""
    exit 1
fi

NODE_VER=$(node -v)
echo "  [✓] Node.js $NODE_VER"
echo ""
echo "  正在启动 DeepSeek Harness ..."
echo "  (首次运行会自动下载依赖，请耐心等待)"
echo ""

# Run dsh
npx @deepseek-ai/dsh web "$@"

if [ $? -ne 0 ]; then
    echo ""
    echo "  [✗] 启动失败，请检查网络连接或 Node.js 版本"
    exit 1
fi
