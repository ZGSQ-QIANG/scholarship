from playwright.sync_api import sync_playwright
from markdownify import markdownify as md
from concurrent.futures import ThreadPoolExecutor
import time
import asyncio
# 创建线程池
executor = ThreadPoolExecutor(max_workers=3)

def _sync_certificate_verify(vcode,name=None, **kwargs):
    """
    验证学信网学籍在线验证码
    参数:
        vcode (str): 学籍在线验证码，格式如 ACY3RBVSBQQDN6Z1

    返回:
        None: 如果验证码无效
        str: 如果验证码有效，返回学籍信息的 Markdown 格式内容
    """
    # 获取函数参数签名，检查多余参数并丢弃
    if kwargs:
        print(f"⚠️ 模型多传了这些参数(已忽略): {kwargs}")

    print(f"[Service: CHSI] 开始验证学籍证明: vcode={vcode}")

    url = f"https://www.chsi.com.cn/xlcx/bg.do?vcode={vcode}&srcid=bgcx"

    with sync_playwright() as p:
        # 启动浏览器
        browser = p.chromium.launch(
            headless=True,  # 生产环境使用无头模式
            args=['--disable-blink-features=AutomationControlled']
        )

        # 创建上下文，模拟真实浏览器
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='zh-CN'
        )

        page = context.new_page()

        try:
            # 访问页面
            print(f"   [Service] 正在访问学信网...")
            page.goto(url, timeout=30000)

            # 等待反爬虫机制完成并重新加载页面
            # 通常需要 8-12 秒
            print(f"   [Service] 等待页面加载...")
            time.sleep(10)

            # 检查是否有 resultTable（学籍信息表）
            result_table = page.query_selector('#resultTable')

            if result_table:
                name_val = page.query_selector('#resultTable .report-info-item:has(.label:has-text("姓名")) .value')
                official_name =  name_val.inner_text()
                official_name = official_name.strip()
                user_name = name.strip()

                if official_name == user_name:
                    print(f"   [Service] ✓ 验证码有效，获取学籍信息")
                    # 获取 HTML 内容
                    html_content = result_table.inner_html()

                    # 转换为 Markdown
                    markdown_content = md(html_content)

                    return {
                        "status": "valid",
                        "message": "验证码有效，学籍信息如下：",
                        "detail":{
                            "markdown": markdown_content
                        }
                    }
                # 找到学籍信息
                else:
                    print(f"   [Service] ✓ 验证码有效，但姓名不匹配 (页面姓名: {official_name}, 提供姓名: {user_name})")

                    return{
                        "status": "name_mismatch",
                        "message": f"验证码有效，但姓名不匹配 (页面姓名: {official_name}, 提供姓名: {user_name})"
                    }
               
            else:
                # 验证码无效
                result_error=page.query_selector('.result-error h2')
                if result_error:    
                    error_text=result_error.inner_text()
                    error_text = error_text.strip()
                    print(f"   [Service] ✗ {error_text}")
                    return {
                        "status": "invalid",
                        "message": f"{error_text}",
                        "verified": False  # Explicitly mark as verified=False
                    }
                else:
                    # 既没有结果表，也没有标准错误提示
                    print(f"   [Service] ✗ 未知错误，无法找到学籍信息或错误提示")
                    return {
                        "status": "error",
                        "message": "未知错误，无法找到学籍信息或错误提示",
                        "verified": False
                    }

        except Exception as e:
            print(f"   [Error] 验证过程发生错误: {e}")
            return {
                "status": "error",
                "message": f"验证过程发生错误: {e}"
            }
        finally:
            context.close()
            browser.close()

async def certificate_verify(vcode, name=None, **kwargs):
    """异步包装器"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, _sync_certificate_verify, vcode, name, **kwargs)