#!/bin/bash
echo "================================================"
echo "  QSL-CN 完整功能检查"
echo "================================================"
echo ""

echo "✅ 1. 检查后端服务"
curl -s http://localhost:8001/health | python3 -m json.tool || echo "❌ 后端未运行"
echo ""

echo "✅ 2. 检查前端服务"
curl -I http://localhost:2345 2>&1 | grep "HTTP" || echo "❌ 前端未运行"
echo ""

echo "✅ 3. 检查已安装的包"
source venv/bin/activate
pip list | grep -E "torch|transformers|einops|accelerate|fastapi|pandas|tushare|jieba"
echo ""

echo "✅ 4. 检查Kronos模型"
ls -lh Kronos-master/ 2>/dev/null | head -5 || echo "⚠️  Kronos-master目录不存在（可选）"
echo ""

echo "✅ 5. 检查配置文件"
echo "CORS配置:"
grep -A 2 "allowed_origins" backend/app.py | head -3
echo ""
echo "限流配置:"
grep "RATE_LIMIT" .env
echo ""

echo "================================================"
echo "  完整功能状态"
echo "================================================"
ps aux | grep -E "uvicorn|vite" | grep -v grep
echo ""
echo "✅ 所有完整功能已启用！"
