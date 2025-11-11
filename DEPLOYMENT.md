# QSL-CN 部署指南

## 快速开始

### 一键启动（推荐）

```bash
./start.sh
```

这将自动：
- 检查Python环境
- 创建虚拟环境（如不存在）
- 安装所有依赖
- 验证配置
- 启动后端服务

### 一键停止

```bash
./stop.sh
```

## 手动部署

### 1. 环境要求

- **Python**: 3.8+
- **Ollama**: 用于AI分析（可选）
- **操作系统**: macOS / Linux / Windows (WSL)

### 2. 安装步骤

#### 2.1 克隆项目

```bash
git clone <repository-url>
cd QSL-CN
```

#### 2.2 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入必要配置：

```bash
# 必须配置
TUSHARE_TOKEN=your_tushare_token_here  # 从 https://tushare.pro/ 获取

# 可选配置
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=deepseek-r1:8b
FRONTEND_URL=https://gp.simon-dd.life  # 你的前端域名
```

#### 2.3 创建虚拟环境

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate     # Windows
```

#### 2.4 安装依赖

```bash
pip install -r backend/requirements.txt
```

**注意**: 如果不需要Kronos K线预测功能，可以注释掉 `requirements.txt` 中的 `torch` 和 `transformers`，这将显著减少安装时间和磁盘占用。

#### 2.5 启动Ollama（可选）

如需完整AI功能：

```bash
# 安装Ollama
# macOS: brew install ollama
# Linux: curl https://ollama.ai/install.sh | sh

# 启动Ollama服务
ollama serve

# 下载模型
ollama pull deepseek-r1:8b
```

如不使用Ollama，系统会自动使用fallback模式生成分析。

### 3. 启动服务

```bash
cd backend
python -m uvicorn app:app --host 0.0.0.0 --port 8001 --reload
```

### 4. 验证安装

访问以下地址验证服务：

- API健康检查: http://localhost:8001/health
- API文档: http://localhost:8001/docs
- 详细健康检查: http://localhost:8001/health/detailed

## 生产环境部署

### 使用Systemd（Linux）

创建 `/etc/systemd/system/qsl-cn.service`:

```ini
[Unit]
Description=QSL-CN Stock Analysis Service
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/QSL-CN
Environment="PATH=/path/to/QSL-CN/venv/bin"
ExecStart=/path/to/QSL-CN/venv/bin/python -m uvicorn app:app --host 0.0.0.0 --port 8001
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable qsl-cn
sudo systemctl start qsl-cn
```

### 使用Docker（推荐生产环境）

```bash
# 构建镜像
docker build -t qsl-cn .

# 运行容器
docker run -d \
  --name qsl-cn \
  -p 8001:8001 \
  -v $(pwd)/.env:/app/.env \
  -v $(pwd)/backend/.cache:/app/backend/.cache \
  qsl-cn
```

### 使用Nginx反向代理

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE支持
        proxy_buffering off;
        proxy_cache off;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }
}
```

## 前端部署

前端应部署到 `https://gp.simon-dd.life`，确保：

1. 在前端配置中设置正确的API地址: `http://your-api-domain:8001`
2. 后端 `.env` 中的 `FRONTEND_URL` 与前端域名一致
3. HTTPS已正确配置

## 性能优化

### 1. 启用缓存

缓存配置在 `.env` 中：

```bash
CACHE_TTL_TECHNICAL=300     # 技术数据缓存5分钟
CACHE_TTL_FUNDAMENTAL=600   # 基本面数据缓存10分钟
CACHE_TTL_MARKET=300        # 市场数据缓存5分钟
```

### 2. 并发配置

```bash
MAX_WORKERS=5              # 并发工作线程数
REQUEST_TIMEOUT=180        # 请求超时时间(秒)
```

### 3. 日志管理

日志自动轮转配置：

```bash
LOG_MAX_BYTES=10485760     # 单个日志文件最大10MB
LOG_BACKUP_COUNT=5         # 保留5个备份文件
```

## 监控与维护

### 健康检查

```bash
# 基础健康检查
curl http://localhost:8001/health

# 详细健康检查
curl http://localhost:8001/health/detailed
```

### 查看日志

```bash
tail -f backend/server.log
```

### 清理缓存

```bash
rm -rf backend/.cache/*
```

## 故障排除

### 1. 端口被占用

```bash
# 查找占用8001端口的进程
lsof -ti:8001

# 杀死进程
lsof -ti:8001 | xargs kill -9
```

### 2. Tushare API限流

如遇到频繁限流，调整 `.env` 配置：

```bash
RATE_LIMIT_PER_MINUTE=50  # 降低调用频率
```

### 3. Ollama连接失败

检查Ollama服务状态：

```bash
curl http://localhost:11434/api/tags
```

如果Ollama不可用，系统会自动使用fallback模式。

### 4. Kronos模型加载失败

如果不需要K线预测功能：
- 删除或重命名 `Kronos-master` 目录
- 系统会自动禁用Kronos功能

如需使用，参考 [KRONOS_SETUP.md](./KRONOS_SETUP.md)

## 安全建议

1. **永远不要提交 `.env` 文件到Git**
2. 定期轮换 Tushare API Token
3. 使用HTTPS部署生产环境
4. 启用防火墙，仅开放必要端口
5. 定期更新依赖包：`pip install -U -r backend/requirements.txt`

## 技术支持

如遇问题，请查看：
- API文档: http://localhost:8001/docs
- 项目README: [README.md](./README.md)
- Kronos设置: [KRONOS_SETUP.md](./KRONOS_SETUP.md)
