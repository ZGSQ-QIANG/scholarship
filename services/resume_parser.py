import os
import json
from zhipuai import ZhipuAI

client = ZhipuAI(api_key=os.getenv("ZHIPU_API_KEY"))

def parse_resume(resume_url: str) -> dict:

    prompt=""" 

        请严格按照以下JSON结构，从附件简历中提取信息。如果信息缺失，请填null。
        {
        "basic_info": { "姓名": "", "学号": "", "导师": ""},
        "papers": [ { "id": "p1", "论文题目": "", "期刊/会议名称": "", "等级": "", "第几作者": "", "状态": "" } ],
        "patents": [ { "id": "pt1", "专利名称": "", "状态": "", "排名": "" } ],
        "contests": [ { "id": "c1", "竞赛名称": "", "获奖等级": "", "时间": "" } ]
        }

 """
    messages=[
    {
        "role": "user",
        "content":[
            {
            "type":"text",
            "text":prompt
            },
            {
            "type":"resume_url",
            "resume_url":f"{resume_url}"
            }
        ]}
    ]

    response = client.chat.completions.create(
        model="glm-4.6v-flash",
        messages=messages,
        response_format={"type":"json_object"} 
    )

    return json.loads(response.choices[0].message.content)