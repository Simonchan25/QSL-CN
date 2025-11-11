#!/usr/bin/env python3
"""
QSL-CN 系统测试脚本
验证所有核心功能是否正常
"""
import sys
import os
from pathlib import Path

# 添加backend到路径
sys.path.insert(0, str(Path(__file__).parent / "backend"))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

def test_imports():
    """测试模块导入"""
    print("=" * 50)
    print("测试模块导入...")
    print("=" * 50)

    try:
        from core.config import settings
        print("✅ Config模块导入成功")
        print(f"   - Server: {settings.SERVER_HOST}:{settings.SERVER_PORT}")
        print(f"   - Frontend: {settings.FRONTEND_URL}")
    except Exception as e:
        print(f"❌ Config模块导入失败: {e}")
        return False

    try:
        from core.utils import clean_nan_values, setup_logger
        print("✅ Utils模块导入成功")
    except Exception as e:
        print(f"❌ Utils模块导入失败: {e}")
        return False

    try:
        from core.rate_limiter import get_tushare_limiter
        print("✅ Rate Limiter模块导入成功")
    except Exception as e:
        print(f"❌ Rate Limiter模块导入失败: {e}")
        return False

    try:
        from core.kronos_predictor import is_kronos_available
        available = is_kronos_available()
        print(f"✅ Kronos Predictor模块导入成功")
        print(f"   - Kronos可用: {available}")
    except Exception as e:
        print(f"❌ Kronos Predictor模块导入失败: {e}")
        return False

    return True


def test_config():
    """测试配置系统"""
    print("\n" + "=" * 50)
    print("测试配置系统...")
    print("=" * 50)

    try:
        from core.config import settings

        # 测试配置验证
        is_valid = settings.validate()
        if is_valid:
            print("✅ 配置验证通过")
        else:
            print("⚠️  配置验证失败（可能缺少TUSHARE_TOKEN）")

        # 测试配置摘要
        summary = settings.get_summary()
        print("✅ 配置摘要生成成功")
        print(f"   - Kronos可用: {summary['kronos']['available']}")
        print(f"   - 限流启用: {summary['rate_limit']['enabled']}")

        return True
    except Exception as e:
        print(f"❌ 配置系统测试失败: {e}")
        return False


def test_utils():
    """测试工具函数"""
    print("\n" + "=" * 50)
    print("测试工具函数...")
    print("=" * 50)

    try:
        from core.utils import clean_nan_values, safe_float, safe_int
        import math

        # 测试NaN清理
        test_data = {
            'a': float('nan'),
            'b': float('inf'),
            'c': [1, 2, float('nan')],
            'd': {'nested': float('inf')}
        }
        cleaned = clean_nan_values(test_data)
        assert cleaned['a'] is None
        assert cleaned['b'] is None
        assert cleaned['c'][2] is None
        print("✅ NaN清理功能正常")

        # 测试安全转换
        assert safe_float(None) == 0.0
        assert safe_float('invalid') == 0.0
        assert safe_int(None) == 0
        print("✅ 安全类型转换功能正常")

        return True
    except Exception as e:
        print(f"❌ 工具函数测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rate_limiter():
    """测试限流器"""
    print("\n" + "=" * 50)
    print("测试限流器...")
    print("=" * 50)

    try:
        from core.rate_limiter import RateLimiter, get_tushare_limiter

        # 测试基础限流器
        limiter = RateLimiter(max_calls=3, time_window=60)
        results = [limiter.is_allowed('test') for _ in range(5)]
        expected = [True, True, True, False, False]
        assert results == expected, f"Expected {expected}, got {results}"
        print("✅ 基础限流器功能正常")

        # 测试Tushare限流器
        tushare_limiter = get_tushare_limiter()
        stats = tushare_limiter.get_stats()
        assert 'minute_remaining' in stats
        assert 'minute_limit' in stats
        print("✅ Tushare限流器功能正常")
        print(f"   - 分钟限制: {stats['minute_limit']}")
        print(f"   - 剩余次数: {stats['minute_remaining']}")

        return True
    except Exception as e:
        print(f"❌ 限流器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cors_config():
    """测试CORS配置"""
    print("\n" + "=" * 50)
    print("测试CORS配置...")
    print("=" * 50)

    try:
        from core.config import settings

        # 检查CORS配置
        assert "https://gp.simon-dd.life" in settings.ALLOWED_ORIGINS
        assert "http://localhost:5173" in settings.ALLOWED_ORIGINS
        print("✅ CORS配置正确")
        print(f"   - 允许的域名: {settings.ALLOWED_ORIGINS}")

        return True
    except Exception as e:
        print(f"❌ CORS配置测试失败: {e}")
        return False


def main():
    """主测试流程"""
    print("\n" + "=" * 60)
    print("QSL-CN 系统功能测试")
    print("=" * 60 + "\n")

    results = []

    # 运行所有测试
    results.append(("模块导入", test_imports()))
    results.append(("配置系统", test_config()))
    results.append(("工具函数", test_utils()))
    results.append(("限流器", test_rate_limiter()))
    results.append(("CORS配置", test_cors_config()))

    # 打印测试结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    passed = 0
    failed = 0

    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name:20s}: {status}")
        if result:
            passed += 1
        else:
            failed += 1

    print("=" * 60)
    print(f"总计: {passed + failed} 个测试, {passed} 通过, {failed} 失败")
    print("=" * 60 + "\n")

    if failed == 0:
        print("🎉 所有测试通过！系统已准备就绪。\n")
        return 0
    else:
        print("⚠️  部分测试失败，请检查配置和依赖。\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
