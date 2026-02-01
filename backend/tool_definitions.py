tools_schema=[
    #论文验证工具
    {
        "type":"function",
        "function":{
            "name":"paper_verify",
            "description":"验证学术论文的真实性及归属。用于核实论文是否已发表，以及用户是否为作者之一。",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "论文的全标题（中文或英文）。"
                    },
                    "doi": {
                        "type": "string",
                        "description": "论文的DOI号 (Digital Object Identifier)，通常以 '10.' 开头，例如 '10.1038/nature12345'。这是最关键的验证字段。"
                    },
                    "authors": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "模型识别出的所有作者姓名列表。"
                    },
                    "publication_date": {
                        "type": "string",
                        "description": "发表年份或日期，用于辅助验证。"
                    }
                }
            },
            "required": ["title", "authors"]
        }
    },
    #学信网学籍在线验证码验证工具
    {
        "type":"function",
        "function":{
            "name":"certificate_verify",
            "description":"验证学信网学籍在线验证码，获取学籍信息。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name":{
                        "type":"string",
                        "description":"姓名"
                    },
                    "vcode": {
                        "type": "string",
                        "description": "学籍在线验证码，格式如 ACY3RBVSBQQDN6Z1"
                    }
                },
                "required": ["vcode"]
            }
        }
    },
    #专利证书验证工具
    {
        "type":"function",
        "function":{
            "name":"patent_verify",
            "description":"验证中国国家知识产权局的专利证书，确认证书的真实性及专利信息。",
            "parameters": {
                "type": "object",
                "properties": {
                    "apply_code": {
                        "type": "string",
                        "description": "专利申请号，例如 '2017105872931'"
                    },
                    "name":{
                        "type":"string",
                        "description":"专利权人姓名"
                    },
                    "title": {
                        "type": "string",
                        "description": "专利名称"
                    }
                },
                "required": ["apply_code", "name", "title"]
            }
        }
    }
]