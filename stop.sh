#!/bin/bash

# ============================================
# QSL-CN 停止脚本
# ============================================

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo "============================================"
echo "  停止 QSL-CN 服务"
echo "============================================"
echo ""

# 停止后端进程
if [ -f .backend.pid ]; then
    BACKEND_PID=$(cat .backend.pid)
    if ps -p $BACKEND_PID > /dev/null 2>&1; then
        log_info "停止后端服务 (PID: $BACKEND_PID)..."
        kill $BACKEND_PID
        sleep 2
        if ps -p $BACKEND_PID > /dev/null 2>&1; then
            log_info "强制停止后端服务..."
            kill -9 $BACKEND_PID
        fi
    fi
    rm .backend.pid
    log_info "后端服务已停止"
else
    log_info "未找到运行中的后端服务"
fi

# 清理端口占用
if lsof -Pi :8001 -sTCP:LISTEN -t >/dev/null 2>&1; then
    log_info "清理端口8001占用..."
    lsof -ti:8001 | xargs kill -9 2>/dev/null || true
fi

echo ""
log_info "所有服务已停止"
echo ""
