# Kronos 模型安装说明

Kronos是用于K线预测的深度学习模型（可选功能）。如果不需要K线预测功能，可以跳过此步骤。

## 方式一：使用HuggingFace Hub（推荐）

项目默认配置会自动从HuggingFace Hub下载模型，无需手动安装Kronos目录。

模型会在首次使用时自动下载到HuggingFace缓存目录。

## 方式二：本地安装Kronos

如果需要使用本地Kronos模型或进行模型微调：

### 1. 克隆Kronos仓库

```bash
cd <项目根目录>
git clone https://github.com/PanopticAI/Kronos.git Kronos-master
```

### 2. 安装Kronos依赖

```bash
cd Kronos-master
pip install -r requirements.txt
```

### 3. 下载预训练模型（可选）

如果需要使用本地模型文件，从HuggingFace下载模型文件到 `Kronos-master/Kronos-base/` 目录。

## 验证安装

运行以下命令验证Kronos是否正确安装：

```bash
python -c "from backend.core.kronos_predictor import is_kronos_available; print('Kronos available:', is_kronos_available())"
```

## 常见问题

### Q: 我必须安装Kronos吗？
A: 不是必须的。Kronos仅用于K线预测功能。如果不使用此功能，系统会自动禁用相关端点。

### Q: Kronos需要GPU吗？
A: 不是必须的，但使用GPU会显著提升预测速度。CPU也可以运行，只是速度较慢。

可以在`.env`文件中配置：
```bash
KRONOS_DEVICE=cuda:0  # 使用GPU
# 或
KRONOS_DEVICE=cpu     # 使用CPU
```

### Q: 如何禁用Kronos功能？
A: 删除或重命名 `Kronos-master` 目录即可。系统会自动检测并禁用Kronos功能。

## 技术支持

如需更多信息，请访问 [Kronos官方仓库](https://github.com/PanopticAI/Kronos)
