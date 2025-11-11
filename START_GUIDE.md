# QSL-CN 快速启动指南

## 🚀 快速启动（推荐）

### 方式一：开发环境（本地调试）

```bash
# 1. 启动后端
cd "/Users/chenfei/Library/Mobile Documents/com~apple~CloudDocs/AI/QSL-CN"
source venv/bin/activate
cd backend
python -m uvicorn app:app --host 0.0.0.0 --port 8001 --reload

# 2. 启动前端（新终端）
cd "/Users/chenfei/Library/Mobile Documents/com~apple~CloudDocs/AI/QSL-CN/frontend"
npm run dev -- --config vite.config.dev.js
```

**访问地址**:
- 前端: http://localhost:2345
- API: http://localhost:8001/docs

---

### 方式二：生产环境（域名访问）

```bash
# 1. 启动后端
cd "/Users/chenfei/Library/Mobile Documents/com~apple~CloudDocs/AI/QSL-CN"
source venv/bin/activate
cd backend
python -m uvicorn app:app --host 0.0.0.0 --port 8001

# 2. 启动前端（新终端）
cd "/Users/chenfei/Library/Mobile Documents/com~apple~CloudDocs/AI/QSL-CN/frontend"
npm run dev  # 使用默认配置（hmr: false）
```

**访问地址**:
- 前端: https://gp.simon-dd.life
- API: https://gp.simon-dd.life:8001

---

## 📝 配置说明

### 开发环境 vs 生产环境

| 项目 | 开发环境 | 生产环境 |
|-----|---------|---------|
| Vite配置 | `vite.config.dev.js` | `vite.config.js` |
| HMR热更新 | ✅ 启用 | ❌ 禁用 |
| 访问方式 | localhost:2345 | gp.simon-dd.life |
| WebSocket | ✅ 可用 | ❌ 禁用 |

### 为什么生产环境禁用HMR？

生产环境使用HTTPS域名（`https://gp.simon-dd.life`），HMR的WebSocket连接会失败，因此禁用。

---

## 🛑 停止服务

```bash
# 停止后端
pkill -f "uvicorn app:app"

# 停止前端
pkill -f "vite --host"
```

或使用停止脚本：
```bash
./stop.sh
```

---

## ✅ 验证服务状态

```bash
# 检查后端
curl http://localhost:8001/health

# 检查前端
curl -I http://localhost:2345

# 查看运行的进程
ps aux | grep -E "uvicorn|vite"
```

---

## 🔧 常见问题

### Q: 前端显示"待处理"或HMR错误？
**A**: 如果使用生产配置（`vite.config.js`），HMR被禁用是正常的。使用开发配置即可：
```bash
npm run dev -- --config vite.config.dev.js
```

### Q: 后端无法访问？
**A**: 检查是否在虚拟环境中运行：
```bash
source venv/bin/activate
cd backend
python -m uvicorn app:app --host 0.0.0.0 --port 8001 --reload
```

### Q: 依赖安装失败？
**A**: Python 3.13兼容性问题已解决。如果还有问题：
```bash
pip install --upgrade pip
pip install -r backend/requirements.txt
```

---

## 📊 端口使用

| 端口 | 服务 | 说明 |
|-----|------|------|
| 2345 | 前端开发服务器 | Vite |
| 8001 | 后端API | FastAPI |
| 11434 | Ollama（可选） | AI模型服务 |

---

## 💡 推荐开发流程

1. **启动后端**: `cd backend && uvicorn app:app --reload`
2. **启动前端**: `cd frontend && npm run dev -- --config vite.config.dev.js`
3. **访问**: http://localhost:2345
4. **查看日志**: 后端有详细日志，前端在浏览器控制台

---

## 🎯 生产部署

参考完整部署文档：[DEPLOYMENT.md](./DEPLOYMENT.md)

生产环境需要：
- Nginx反向代理
- HTTPS证书
- 使用 `vite.config.js`（禁用HMR）
- 配置正确的域名
