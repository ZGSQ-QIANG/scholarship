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
    }
]