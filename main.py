import os
import json
import base64
from io import BytesIO
from dotenv import load_dotenv
from zhipuai import ZhipuAI
from tool_definitions import tools_schema
from services.paper_verify import paper_verify
import fitz

load_dotenv()

client = ZhipuAI(api_key=os.getenv("ZHIPU_API_KEY"))

# ==========================================
# 1. PDF 转图片并编码
# ==========================================
pdf_path = os.getenv("PAPER_PATH", "./paper1.pdf")  # 支持环境变量覆盖路径
print("正在处理PDF文件...")

# 路径规范化与存在性检查；若不存在则尝试在工作区内寻找任意 PDF
pdf_path = os.path.abspath(pdf_path)
if not os.path.exists(pdf_path):
    print(f"未找到PDF: {pdf_path}")
    workspace_dir = os.path.abspath(os.getcwd())
    candidates = []
    for root, _, files in os.walk(workspace_dir):
        for f in files:
            if f.lower().endswith(".pdf"):
                candidates.append(os.path.join(root, f))
    if candidates:
        pdf_path = candidates[0]
        print(f"已自动选择PDF: {pdf_path}")
    else:
        raise FileNotFoundError("工作区内未找到任何PDF，请设置环境变量 PAPER_PATH 或将文件命名为 paper.pdf 放在项目根目录")

# 将PDF第一页转为图片（如果是多页论文可以处理多页）
encoded_string = None



try:
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    pix = page.get_pixmap(dpi=200)
    buffered = BytesIO(pix.tobytes("png"))
    encoded_string = base64.b64encode(buffered.getvalue()).decode("utf-8")
    doc.close()
    print("PDF渲染成功（PyMuPDF）")
except Exception as ee:
    raise RuntimeError(f"无法渲染PDF，请确认已安装 Poppler 或 PyMuPDF。原始错误: {ee}")

# ==========================================
# 2. 第一次调用：让模型识别论文信息
# ==========================================
print("发送给模型识别...")
messages = [
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": "请识别这篇论文的关键信息，包括：标题、作者列表、DOI号（如果有）、发表日期。如果这是一篇学术论文，请调用论文验证工具进行验证。"
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{encoded_string}"
                }
            }
        ]
    }
]

response = client.chat.completions.create(
    model="GLM-4.6V-Flash",
    messages=messages,
    tools=tools_schema,
    tool_choice="auto"
)

# ==========================================
# 3. 处理模型响应
# ==========================================
assistant_message = response.choices[0].message

# 如果模型要调用工具
if assistant_message.tool_calls:
    print("\n模型请求调用工具...")
    
    # 将assistant的消息添加到对话历史
    messages.append(assistant_message.model_dump())
    
    # 处理每个工具调用
    for tool_call in assistant_message.tool_calls:
        function_name = tool_call.function.name
        function_args = json.loads(tool_call.function.arguments)
        
        print(f"\n调用工具: {function_name}")
        print(f"参数: {json.dumps(function_args, ensure_ascii=False, indent=2)}")
        
        # 调用实际的验证函数
        if function_name == "paper_verify":
            result = paper_verify(
                title=function_args.get("title"),
                authors=function_args.get("authors"),
                doi=function_args.get("doi")
            )
        else:
            result = {"error": "未知的工具"}
        
        print(f"验证结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        # 将工具调用结果添加到消息历史
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": json.dumps(result, ensure_ascii=False)
        })
    
    # ==========================================
    # 4. 第二次调用：让模型根据验证结果给出最终回答
    # ==========================================
    print("\n请求模型生成最终答案...")
    # 强化指令：要求输出最终判定（验证通过/不通过）与简要理由
    messages.append({
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": "请根据工具返回结果，给出明确结论：\n- 若工具返回 status=success，输出：验证通过，并简要说明匹配到的作者/DOI等依据。\n- 若工具返回 status=warning 或 failed，输出：验证不通过（或存在疑问），并简要说明原因。\n只输出中文结论与理由，尽量简洁。"
            }
        ]
    })

    final_response = client.chat.completions.create(
        model="GLM-4.6V-Flash",
        messages=messages
    )
    
    final_answer = final_response.choices[0].message.content
    print(f"\n{'='*50}")
    print("最终回答:")
    print(final_answer)
    print(f"{'='*50}")

else:
    # 模型没有调用工具，直接输出回答
    print(f"\n模型回答: {assistant_message.content}")
