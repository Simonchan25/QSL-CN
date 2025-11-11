#!/bin/bash
# 前端开发启动脚本 - 使用构建+预览模式

cd "$(dirname "$0")"

echo "🔨 构建前端..."
npm run build

if [ $? -ne 0 ]; then
    echo "❌ 构建失败"
    exit 1
fi

echo "✅ 构建成功"
echo "🚀 启动预览服务器在 http://localhost:2345/"
echo ""
echo "💡 修改代码后，运行 'npm run build' 重新构建"
echo "   或运行 './start-dev.sh' 重新启动"
echo ""
echo "按 Ctrl+C 停止服务"
echo ""

npm run preview
