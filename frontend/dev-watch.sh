#!/bin/bash
# 前端开发监视脚本 - 自动构建并预览

echo "🔨 正在首次构建..."
npm run build

echo "🚀 启动预览服务器..."
npm run preview &
PREVIEW_PID=$!

echo "👀 开始监视文件变化..."
echo "按 Ctrl+C 停止"

# 清理函数
cleanup() {
    echo ""
    echo "⏹️  停止服务..."
    kill $PREVIEW_PID 2>/dev/null
    exit 0
}

trap cleanup INT TERM

# 监视src目录变化，自动重新构建
while true; do
    # 使用fswatch监视变化
    fswatch -1 -r src/ index.html vite.config.js > /dev/null 2>&1
    echo "📝 检测到文件变化，重新构建..."
    npm run build
    echo "✅ 构建完成"
done
