"""
配置管理模块
集中管理所有配置项，从环境变量读取配置
"""
import os
from typing import List
from pathlib import Path


class Settings:
    """应用配置类"""

    # 项目路径
    BASE_DIR: Path = Path(__file__).parent.parent
    ROOT_DIR: Path = BASE_DIR.parent

    # Tushare配置
    TUSHARE_TOKEN: str = os.getenv("TUSHARE_TOKEN", "")

    # Ollama配置
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "deepseek-r1:8b")
    OLLAMA_NUM_PREDICT: int = int(os.getenv("OLLAMA_NUM_PREDICT", "8192"))
    OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", "300"))

    # 服务器配置
    SERVER_HOST: str = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT: int = int(os.getenv("SERVER_PORT", "8001"))

    # CORS配置
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",
        "https://gp.simon-dd.life",
    ]

    # 缓存配置
    CACHE_TTL_TECHNICAL: int = int(os.getenv("CACHE_TTL_TECHNICAL", "300"))
    CACHE_TTL_FUNDAMENTAL: int = int(os.getenv("CACHE_TTL_FUNDAMENTAL", "600"))
    CACHE_TTL_MARKET: int = int(os.getenv("CACHE_TTL_MARKET", "300"))
    CACHE_MAX_SIZE: int = int(os.getenv("CACHE_MAX_SIZE", "1000"))
    CACHE_DIR: Path = BASE_DIR / ".cache"

    # 日志配置
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "server.log")
    LOG_MAX_BYTES: int = int(os.getenv("LOG_MAX_BYTES", "10485760"))  # 10MB
    LOG_BACKUP_COUNT: int = int(os.getenv("LOG_BACKUP_COUNT", "5"))

    # 限流配置
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

    # 并发配置
    MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", "5"))
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "180"))

    # Kronos模型配置
    KRONOS_DIR: Path = ROOT_DIR / "Kronos-master"
    KRONOS_TOKENIZER_PATH: str = os.getenv("KRONOS_TOKENIZER_PATH", "NeoQuasar/Kronos-Tokenizer-base")
    KRONOS_MODEL_PATH: str = os.getenv("KRONOS_MODEL_PATH", "NeoQuasar/Kronos-base")
    KRONOS_DEVICE: str = os.getenv("KRONOS_DEVICE", "cpu")  # cpu, cuda:0, mps

    @classmethod
    def validate(cls) -> bool:
        """
        验证配置是否正确

        Returns:
            bool: 配置是否有效
        """
        errors = []

        # 验证必需的配置
        if not cls.TUSHARE_TOKEN:
            errors.append("TUSHARE_TOKEN not set")

        # 验证目录权限
        try:
            cls.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            errors.append(f"Cannot create cache directory: {e}")

        if errors:
            print("Configuration errors:")
            for error in errors:
                print(f"  - {error}")
            return False

        return True

    @classmethod
    def get_summary(cls) -> dict:
        """
        获取配置摘要（隐藏敏感信息）

        Returns:
            dict: 配置摘要
        """
        return {
            "server": {
                "host": cls.SERVER_HOST,
                "port": cls.SERVER_PORT,
            },
            "ollama": {
                "url": cls.OLLAMA_URL,
                "model": cls.OLLAMA_MODEL,
            },
            "cache": {
                "ttl_technical": cls.CACHE_TTL_TECHNICAL,
                "ttl_fundamental": cls.CACHE_TTL_FUNDAMENTAL,
                "ttl_market": cls.CACHE_TTL_MARKET,
                "max_size": cls.CACHE_MAX_SIZE,
            },
            "logging": {
                "level": cls.LOG_LEVEL,
                "file": cls.LOG_FILE,
            },
            "rate_limit": {
                "enabled": cls.RATE_LIMIT_ENABLED,
                "per_minute": cls.RATE_LIMIT_PER_MINUTE,
            },
            "kronos": {
                "available": cls.KRONOS_DIR.exists(),
                "device": cls.KRONOS_DEVICE,
            },
        }


# 创建全局配置实例
settings = Settings()
