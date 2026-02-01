import os
import json
from zhipuai import ZhipuAI

def parse_resume(resume_url: str, client:ZhipuAI) -> dict:
    print(f"[Parser] 开始上传文件: {resume_url}")
    try:
        #上传文件获取 resume_id
        with open(resume_url, "rb") as f:
            file_obj = client.files.create(file=f, purpose="file-extract")
            file_content=client.files.content(file_id=file_obj.id).content.decode()
        #    file_id = file_obj.id
       
    #print(f"Service: 文件上传成功，文件ID={file_id}") 
        prompt=""" 

        请严格按照以下JSON结构，从附件简历中提取信息。如果信息缺失，请填null。
        {
        "basic_info": { "姓名": "", "学号": "", "导师": ""},
        "papers": [ { "id": "", "论文题目": "", "期刊/会议名称": "", "等级": "", "第几作者": "", "状态": "已录用或已发表" } ],
        "patents": [ { "id": "", "专利名称": "", "状态": "", "时间": "" } ],
        "contests": [ { "id": "", "竞赛名称": "", "获奖等级": "", "时间": "" } ]
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
                "type":"text",
                "text": file_content
                }
            ]}
        ]

        response = client.chat.completions.create(
            model="glm-4.6v-flash",
            messages=messages,
            response_format={"type":"json_object"} 
        )
        print(response.choices[0].message.content)
        return json.loads(response.choices[0].message.content) 
    except Exception as e:
        print(f"[Parser] 解析简历时出错: {e}")
        import traceback
        traceback.print_exc()
        
        # 返回一个默认结构，避免前端崩溃
        return {
            "basic_info": {"姓名": "解析失败", "学号": "", "导师": ""},
            "papers": [],
            "patents": [],
            "contests": [],
            "error": str(e)
        }