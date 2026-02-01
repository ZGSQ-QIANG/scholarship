from playwright.sync_api import sync_playwright
import time
from concurrent.futures import ThreadPoolExecutor
import asyncio

# 创建线程池
executor = ThreadPoolExecutor(max_workers=3)
#专利证书验证
def _sync_patent_verify(apply_code,name,title, **kwargs):
    # 获取函数参数签名，检查多余参数并丢弃
    if kwargs:
        print(f"⚠️ 模型多传了这些参数(已忽略): {kwargs}")

    print(f"[Service: PatentOffice] 开始验证专利证书: apply_code={apply_code},name={name} ")

    url=f"http://epub.cnipa.gov.cn/Index"

    with sync_playwright() as p:
        # 启动浏览器
        browser = p.chromium.launch(
            headless=True,  # 生产环境使用无头模式
            args=['--disable-blink-features=AutomationControlled']
        )

        # 创建上下文，模拟真实浏览器
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            locale='zh-CN'
        )

        page=context.new_page()

        try:

            print(f"   [Service] 正在访问中国专利网...")
            page.goto(url, timeout=30000)

            # 等待反爬虫机制完成并重新加载页面
            # 通常需要 8-12 秒
            print(f"   [Service] 等待页面加载...")
            time.sleep(10)

            print(f"   [Service] 填写查询信息...")
            page.fill('input#searchStr', apply_code)

            print(f"   [Service] 提交查询...")
            
            #点击class为sbtn的按钮
            page.click("button.sbtn")

            # 等待结果加载
            # 3. 等待查询结果出现 (例如，等待结果列表的表格出现)
            print(f"   [Service] 等待查询结果...")
            time.sleep(10)
            try:
                page.wait_for_selector('#result', timeout=5000)
            except Exception:
                print(f"   [Service] ✗ 未找到结果表单 #result")
                return {
                    "status": "failed",
                    "message": "未找到查询结果，申请号无效。",
                    "verified": False
                }

            # 检查是否有结果
            web_result = page.query_selector('#result')
            
            if web_result:
                print(f"   [Service] ✓ 查询成功，获取专利信息")
                # 获取专利标题
                #result_text = web_result.inner_text().strip()
                official_t =  web_result.query_selector('h1.title')
                if official_t:
                    raw_title=official_t.inner_text()
                    raw_title=raw_title.strip()

                    #清理字符串，找到“]”，取后面部分
                    clean_title=raw_title
                    if "]" in raw_title:
                        clean_title=raw_title.split("]",1)[-1].strip()                

                    official_title=clean_title
                    print(f"   [Service] 获取到的专利标题: {official_title}")                    
                else:
                    print(f"   [Warning] ✗ 未找到标题元素")
            
                #获取发明人信息
                official_i=  web_result.query_selector('dl:has-text("发明人：") dd')
                #所有发明人
                official_inventors=[]
                if official_i:
                    all_inventors= official_i.inner_text()
                    all_inventors=all_inventors.strip()
                    #发明人可能有多个，用分号分隔
                    official_inventors=[inv.strip() for inv in all_inventors.split(";")]
                    print(f"   [Service] 获取到的发明人列表: {official_inventors}")
                
                
                #忽略大小写和前后空格
                title_match = title.lower().strip() in official_title.lower()
                #检查传入的name是否在官方列表中
                name_match=name.strip() in official_inventors

                if name_match and title_match:
                    print(f"   [Service] ✓ 专利证书信息匹配成功")
                    return {
                        "status": "success",
                        "message": "专利证书信息匹配成功，证书真实有效。",
                        "detail":{
                            "official_title": official_title,
                            "official_inventors": official_inventors,
                            "matched_name": name
                        }
                    }
                else:
                    fail_reason=[]
                    if not name_match:
                        fail_reason.append("发明人列表中未找到'" + name + "'")
                    if not title_match:
                        fail_reason.append("专利标题不匹配")

                    print(f"   [Service] ✗ 专利证书信息不匹配: {', '.join(fail_reason)}")
                    return {
                        "status": "failed",
                        "message": f"专利信息不匹配: {', '.join(fail_reason)}。",
                        "detail": {
                            "provided_title": title, "official_title": official_title,
                            "provided_name": name, "official_inventors": official_inventors
                        }
                    }
            else:
                print(f"   [Service] ✗ 未找到专利信息，可能申请号无效")
                return {
                    "status": "failed",
                    "message": "未找到专利信息，申请号无效。",
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

async def patent_verify(apply_code,name,title, **kwargs):
    """异步包装器"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, _sync_patent_verify, apply_code, name, title, **kwargs)

