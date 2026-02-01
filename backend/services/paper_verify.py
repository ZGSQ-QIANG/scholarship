import requests
#[基于 CrossRef 官方 API] 验证学术论文
def paper_verify(title, authors, doi=None, **kwargs):
    # 获取函数参数签名，检查多余参数并丢弃
    if kwargs:
        print(f"⚠️ 模型多传了这些参数(已忽略): {kwargs}")

    # 1. 配置 API 和 礼貌头 (Polite Header)
    base_url = "https://api.crossref.org/works"
    
    # 告诉 CrossRef "是谁在调用"，进入快车道，不会被轻易限流。
    headers = {
        "User-Agent": "PaperVerifierTool/1.0 (mailto:1140009502@qq.com)"
    }

    print(f"   [Service: CrossRef] 开始验证: DOI={doi} | Title={title}")

    found_data = None


    # 2. 策略 A: 有 DOI 直接查 (最准)
    if doi:
        try:
            # 1. 清洗 DOI (用户上传 "https://doi.org/10.xxx"，去掉前缀)
            clean_doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "").strip()
            
            # 2. 拼接 URL
            target_url = f"{base_url}/{clean_doi}"
            
            # 3. 发送请求
            resp = requests.get(target_url, headers=headers, timeout=5)
            
            if resp.status_code == 200:
                # CrossRef 返回的数据都在 'message' 字段里
                found_data = resp.json()['message']
                print("   [Service] DOI 精确匹配成功！")
            else:
                print(f"   [Service] DOI 查询无结果 (Code: {resp.status_code})")
                
        except Exception as e:
            print(f"   [Error] DOI 请求发生错误: {e}")


    # 3. 策略 B: 没 DOI (或查不到) 用标题搜
    if not found_data and title:
        try:
            print("   [Service] 尝试使用标题搜索...")
            params = {
                "query.title": title, # 只搜标题
                "rows": 1,            # 只要第1条检索结果
                "select": "title,DOI,author,publisher,created,container-title" # 只返回这几个字段
            }
            
            resp = requests.get(base_url, params=params, headers=headers, timeout=5)
            
            if resp.status_code == 200:
                items = resp.json()['message']['items']
                if items:
                    found_data = items[0]
                    print("   [Service] 标题搜索匹配成功！")
        except Exception as e:
            print(f"   [Error] 标题搜索发生错误: {e}")


    # 4. 结果判定与作者核对
    if not found_data:
        return {
            "status": "failed", 
            "message": "未在 CrossRef 数据库中检索到该论文，请检查是否已正式发表。"
        }
    #获取返回论文标题
    official_title= found_data.get('title', [''])[0]
    #获取返回论文期刊或会议
    official_journal= found_data.get('container-title', [''])[0]
    # 比对用户提供的标题和官方标题（全小写去空格）
    user_t=title.strip().lower()
    official_t=official_title.strip().lower()

    if user_t != official_t:
        print(f"   [Warning] 用户标题与官方标题不完全匹配: 用户='{user_t}' , 官方='{official_t}'")
        return{
            "status": "warning",
            "message": "论文题目不匹配，未找到该论文，请确认。",
            "detail": {
                "provided_title": title,
                "official_title": official_title,
                "official_doi": found_data.get('DOI')
            }
        }
    print("   [success] 论文标题匹配通过。")

    # 提取真实作者列表 (API 返回的是列表结构，把它拼成字符串方便比对)
    # 数据样例: [{'given': 'J.', 'family': 'Smith'}, {'given': 'A.', 'family': 'Doe'}]
    real_authors_raw = found_data.get('author', [])
    
    # 拼装成 ["j. smith", "a. doe"] 这样的全小写列表
    real_authors_formatted = []
    for person in real_authors_raw:
        # 有些数据可能没有 given name 或 family name，要做容错
        full_name = f"{person.get('given', '')} {person.get('family', '')}"
        real_authors_formatted.append(full_name.lower().strip())


    # 比对用户提供的作者
    matched_authors = []
    for user_auth in authors:
        user_auth_lower = user_auth.lower()
        # 只要包含就算匹配 (比如 "Zhang" 在 "San Zhang" 里)
        is_match = False
        for real_auth in real_authors_formatted:
            if user_auth_lower in real_auth or real_auth in user_auth_lower:
                is_match = True
                break
        
        if is_match:
            matched_authors.append(user_auth)

    # 5. 返回最终结果
    if matched_authors:
        
        return {
            "status": "success",
            "message": "论文验证通过",
            "detail": {
                "title": official_title,     
                "doi": found_data.get('DOI'),
                "publisher": found_data.get('publisher'),
                "journal": official_journal,
                "matched_authors": matched_authors
            }
        }
    else:
        return {
            "status": "warning",
            "message": "论文真实存在，但在作者列表中未找到您的名字。",
            "detail": {
                "title": official_title,
                "official_authors": real_authors_formatted
            }
        }