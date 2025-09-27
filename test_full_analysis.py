#!/usr/bin/env python3
"""
完整测试前端点击分析按钮的流程
使用无头浏览器模拟用户操作，定位问题所在
"""

import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import requests

def test_backend_api():
    """先测试后端API是否正常"""
    print("=== 测试后端API ===")
    try:
        # 测试健康检查
        resp = requests.get("http://localhost:8001/health")
        print(f"健康检查: {resp.status_code} - {resp.text}")

        # 测试股票解析
        resp = requests.get("http://localhost:8001/resolve?name=平安银行")
        print(f"股票解析: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"解析成功: {data.get('name')} ({data.get('ts_code')})")

        # 测试专业分析接口
        print("\n测试专业分析接口...")
        resp = requests.get("http://localhost:8001/analyze/professional?name=平安银行&force=true")
        print(f"专业分析: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"分析返回字段: {list(data.keys())}")
            if 'text' in data:
                print(f"报告长度: {len(data['text'])} 字符")
            if 'score' in data:
                print(f"评分: {data['score']}")
        else:
            print(f"分析失败: {resp.text[:200]}")

        return True
    except Exception as e:
        print(f"后端API测试失败: {e}")
        return False

def test_frontend_with_selenium():
    """使用Selenium测试前端"""
    print("\n=== 使用Selenium测试前端 ===")

    # 配置Chrome无头模式
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 无头模式
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")

    # 启用控制台日志捕获
    chrome_options.add_experimental_option('w3c', True)
    chrome_options.set_capability('goog:loggingPrefs', {'browser': 'ALL', 'performance': 'ALL'})

    driver = webdriver.Chrome(options=chrome_options)

    try:
        # 访问前端页面
        print("1. 访问前端页面...")
        driver.get("http://localhost:2345")
        time.sleep(2)

        # 获取页面标题
        print(f"页面标题: {driver.title}")

        # 查找输入框
        print("\n2. 查找股票输入框...")
        try:
            # 尝试多种选择器
            selectors = [
                "input[type='text']",
                "input[placeholder*='股票']",
                ".stock-input",
                "#stockInput"
            ]

            input_element = None
            for selector in selectors:
                try:
                    input_element = driver.find_element(By.CSS_SELECTOR, selector)
                    print(f"找到输入框: {selector}")
                    break
                except:
                    continue

            if not input_element:
                input_element = driver.find_element(By.XPATH, "//input[@type='text']")
                print("通过XPath找到输入框")

        except Exception as e:
            print(f"未找到输入框: {e}")
            # 打印页面HTML帮助调试
            print("页面HTML片段:")
            print(driver.find_element(By.TAG_NAME, "body").get_attribute("innerHTML")[:1000])
            return

        # 输入股票名称
        print("\n3. 输入股票名称...")
        input_element.clear()
        input_element.send_keys("平安银行")
        time.sleep(1)

        # 查找分析按钮
        print("\n4. 查找分析按钮...")
        try:
            # 尝试多种选择器
            button_selectors = [
                "button:contains('分析')",
                "button.analyze-btn",
                "#analyzeBtn",
                "//button[contains(text(), '分析')]"
            ]

            analyze_button = None
            # CSS选择器
            for selector in button_selectors[:3]:
                try:
                    analyze_button = driver.find_element(By.CSS_SELECTOR, selector)
                    print(f"找到按钮: {selector}")
                    break
                except:
                    continue

            # XPath选择器
            if not analyze_button:
                try:
                    analyze_button = driver.find_element(By.XPATH, "//button[contains(text(), '分析')]")
                    print("通过XPath找到分析按钮")
                except:
                    # 尝试查找所有按钮
                    buttons = driver.find_elements(By.TAG_NAME, "button")
                    for btn in buttons:
                        if "分析" in btn.text:
                            analyze_button = btn
                            print(f"找到按钮，文本: {btn.text}")
                            break

        except Exception as e:
            print(f"未找到分析按钮: {e}")
            return

        # 获取网络请求日志（用于调试）
        print("\n5. 准备监控网络请求...")

        # 点击分析按钮
        print("\n6. 点击分析按钮...")
        driver.execute_script("arguments[0].scrollIntoView();", analyze_button)
        analyze_button.click()

        # 等待并监控结果
        print("\n7. 等待分析结果...")
        time.sleep(5)  # 等待5秒

        # 获取浏览器控制台日志
        print("\n8. 检查控制台日志...")
        logs = driver.get_log('browser')
        for log in logs:
            if log['level'] in ['SEVERE', 'ERROR']:
                print(f"控制台错误: {log['message']}")
            elif 'fetch' in log['message'].lower() or 'xhr' in log['message'].lower():
                print(f"网络请求: {log['message']}")

        # 检查是否有结果显示
        print("\n9. 检查结果区域...")
        try:
            # 查找可能的结果容器
            result_selectors = [
                ".analysis-result",
                ".result-container",
                "#result",
                "[class*='result']",
                "[id*='result']"
            ]

            for selector in result_selectors:
                try:
                    result_element = driver.find_element(By.CSS_SELECTOR, selector)
                    if result_element.is_displayed():
                        print(f"找到结果区域: {selector}")
                        print(f"结果内容预览: {result_element.text[:200]}")
                        break
                except:
                    continue

        except Exception as e:
            print(f"未找到结果区域: {e}")

        # 检查是否有加载指示器
        print("\n10. 检查加载状态...")
        loading_selectors = [".loading", ".spinner", "[class*='loading']", "[class*='spinner']"]
        for selector in loading_selectors:
            try:
                loading = driver.find_element(By.CSS_SELECTOR, selector)
                if loading.is_displayed():
                    print(f"发现加载指示器: {selector}")
            except:
                continue

        # 获取网络性能日志
        print("\n11. 分析网络请求...")
        performance_logs = driver.get_log('performance')
        for log in performance_logs[-20:]:  # 最后20条
            message = json.loads(log['message'])
            if message['message']['method'] == 'Network.responseReceived':
                response = message['message']['params']['response']
                if 'analyze' in response['url']:
                    print(f"API请求: {response['url']} - 状态: {response['status']}")

        # 截图保存（即使是无头模式也可以截图）
        print("\n12. 保存截图...")
        driver.save_screenshot("test_result.png")
        print("截图已保存为 test_result.png")

    except Exception as e:
        print(f"测试过程出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()

def main():
    """主测试流程"""
    print("开始完整的分析功能测试\n")

    # 先测试后端
    backend_ok = test_backend_api()
    if not backend_ok:
        print("\n后端API有问题，请先修复后端")
        return

    # 再测试前端
    print("\n后端API正常，开始测试前端...")
    test_frontend_with_selenium()

    print("\n测试完成！")

if __name__ == "__main__":
    main()