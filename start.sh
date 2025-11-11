#!/bin/bash

# ============================================
# QSL-CN 一键启动脚本
# ============================================

set -e  # 遇到错误立即退出

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 打印Banner
print_banner() {
    echo "============================================"
    echo "  QSL-CN - 股票市场分析系统"
    echo "  一键启动脚本"
    echo "============================================"
    echo ""
}

# 检查Python环境
check_python() {
    log_info "检查Python环境..."

    if ! command_exists python3; then
        log_error "Python3 未安装，请先安装Python 3.8+"
        exit 1
    fi

    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    log_info "Python版本: $PYTHON_VERSION"
}

# 检查虚拟环境
check_venv() {
    log_info "检查虚拟环境..."

    if [ ! -d "venv" ]; then
        log_warn "虚拟环境不存在，正在创建..."
        python3 -m venv venv
        log_info "虚拟环境创建成功"
    fi
}

# 激活虚拟环境
activate_venv() {
    log_info "激活虚拟环境..."
    source venv/bin/activate
}

# 安装依赖
install_dependencies() {
    log_info "检查Python依赖..."

    if [ ! -f "backend/requirements.txt" ]; then
        log_error "requirements.txt 不存在"
        exit 1
    fi

    # 检查是否需要安装依赖
    if ! python -c "import fastapi" 2>/dev/null; then
        log_warn "依赖未安装，开始安装..."
        pip install -r backend/requirements.txt
        log_info "依赖安装完成"
    else
        log_info "依赖已安装"
    fi
}

# 检查配置文件
check_config() {
    log_info "检查配置文件..."

    if [ ! -f ".env" ]; then
        log_warn ".env文件不存在，从.env.example复制..."
        cp .env.example .env
        log_error "请编辑 .env 文件，填入正确的配置（特别是TUSHARE_TOKEN）"
        log_error "编辑完成后重新运行本脚本"
        exit 1
    fi

    # 检查TUSHARE_TOKEN是否配置
    if grep -q "your_tushare_token_here" .env; then
        log_error "请先在.env文件中配置TUSHARE_TOKEN"
        log_error "获取Token: https://tushare.pro/"
        exit 1
    fi

    log_info "配置文件检查通过"
}

# 检查Ollama服务
check_ollama() {
    log_info "检查Ollama服务..."

    OLLAMA_URL=$(grep OLLAMA_URL .env | cut -d '=' -f2)
    OLLAMA_URL=${OLLAMA_URL:-"http://localhost:11434"}

    if curl -s "${OLLAMA_URL}/api/tags" > /dev/null 2>&1; then
        log_info "Ollama服务运行正常"

        # 检查模型
        OLLAMA_MODEL=$(grep OLLAMA_MODEL .env | cut -d '=' -f2)
        OLLAMA_MODEL=${OLLAMA_MODEL:-"deepseek-r1:8b"}

        if curl -s "${OLLAMA_URL}/api/tags" | grep -q "$OLLAMA_MODEL"; then
            log_info "模型 $OLLAMA_MODEL 已安装"
        else
            log_warn "模型 $OLLAMA_MODEL 未安装"
            log_warn "请运行: ollama pull $OLLAMA_MODEL"
        fi
    else
        log_warn "Ollama服务未运行或无法访问"
        log_warn "AI功能将降级使用fallback模式"
        log_warn "如需完整AI功能，请启动Ollama: ollama serve"
    fi
}

# 清理旧进程
cleanup_old_process() {
    log_info "检查并清理旧进程..."

    # 查找并杀死占用8001端口的进程
    if lsof -Pi :8001 -sTCP:LISTEN -t >/dev/null 2>&1; then
        log_warn "端口8001被占用，正在关闭旧进程..."
        lsof -ti:8001 | xargs kill -9 2>/dev/null || true
        sleep 2
    fi
}

# 创建必要的目录
create_directories() {
    log_info "创建必要的目录..."
    mkdir -p backend/.cache
    mkdir -p backend/.cache/reports
    mkdir -p logs
}

# 启动后端服务
start_backend() {
    log_info "启动后端服务..."

    cd backend
    python -m uvicorn app:app --host 0.0.0.0 --port 8001 --reload &
    BACKEND_PID=$!
    cd ..

    echo $BACKEND_PID > .backend.pid
    log_info "后端服务已启动 (PID: $BACKEND_PID)"

    # 等待服务启动
    log_info "等待后端服务就绪..."
    for i in {1..30}; do
        if curl -s http://localhost:8001/health > /dev/null 2>&1; then
            log_info "后端服务就绪!"
            return 0
        fi
        sleep 1
    done

    log_error "后端服务启动超时"
    return 1
}

# 显示服务信息
show_info() {
    echo ""
    echo "============================================"
    log_info "QSL-CN 服务已启动!"
    echo "============================================"
    echo ""
    echo "📊 后端API:     http://localhost:8001"
    echo "📖 API文档:     http://localhost:8001/docs"
    echo "🔍 健康检查:    http://localhost:8001/health"
    echo ""
    echo "🌐 前端域名:    https://gp.simon-dd.life"
    echo ""
    echo "============================================"
    echo ""
    log_info "按 Ctrl+C 停止服务"
    echo ""
}

# 清理函数
cleanup() {
    echo ""
    log_info "正在停止服务..."

    if [ -f .backend.pid ]; then
        BACKEND_PID=$(cat .backend.pid)
        if ps -p $BACKEND_PID > /dev/null 2>&1; then
            kill $BACKEND_PID
            log_info "后端服务已停止"
        fi
        rm .backend.pid
    fi

    log_info "清理完成"
    exit 0
}

# 捕获退出信号
trap cleanup INT TERM

# 主流程
main() {
    print_banner
    check_python
    check_venv
    activate_venv
    install_dependencies
    check_config
    check_ollama
    cleanup_old_process
    create_directories
    start_backend
    show_info

    # 保持脚本运行
    wait
}

# 执行主流程
main
