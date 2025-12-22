import os
import json
import base64
from io import BytesIO
from dotenv import load_dotenv
from PIL import Image
from zhipuai import ZhipuAI
from tool_definitions import tools_schema
from services.paper_verify import paper_verify
from services.certificate_verify import certificate_verify
import fitz

load_dotenv()

client = ZhipuAI(api_key=os.getenv("ZHIPU_API_KEY"))


#扫描目录内所有文件
targe_dir=os.getenv("PAPER_PATH","./")
targe_dir=os.path.abspath(targe_dir)

#定义支持的文件后缀
VALID_EXTENSIONS={'.pdf','.png','.jpg','.jpeg','.bmp','.webp'}

print(f"正在扫描目录：{targe_dir}...")

#收集所有符合条件的文件
input_files=[]

for root, _, files in os.walk(targe_dir):
    for f in files:
        ext=os.path.splitext(f)[1].lower()
        if ext in VALID_EXTENSIONS:
            full_path=os.path.join(root, f)
            input_files.append(full_path)

#分流处理PDF和图片

processed_files_data=[]

def process_PDF(path):
    doc = fitz.open(path)
    page = doc.load_page(0)
    pix = page.get_pixmap(dpi=200)
    buffered = BytesIO(pix.tobytes("jpeg"))
    #encoded_string = base64.b64encode(buffered.getvalue()).decode("utf-8")
    doc.close()
    return buffered

def process_image(path):
    img= Image.open(path)
    #转换颜色，将RGBA转为RGB
    if img.mode in ("RGBA","P"):
        img=img.convert("RGB")

    #尺寸优化
    max_size=1024
    if max(img.size)>max_size:
        img.thumbnail((max_size,max_size))
    buffered=BytesIO()
    #统一保存为JPEG格式，质量85
    img.save(buffered,format="jpeg",quality=85)
    return buffered

for index, file_path in enumerate(input_files):
    try:
        print(f"处理文件 {index+1}/{len(input_files)}: {file_path}")
        ext=os.path.splitext(file_path)[1].lower()
        filename=os.path.basename(file_path)
        img_buffer=None


        if ext=='.pdf':
            img_buffer=process_PDF(file_path)
        else:
            img_buffer=process_image(file_path)
        
        #转为Base64编码
        encoded_string = base64.b64encode(img_buffer.getvalue()).decode("utf-8")
        processed_files_data.append({
            "index":index + 1,
            "filename":filename,
            "base64_image":encoded_string
        })
    except Exception as e:
        print(f"处理文件时出错: {e}")

# ==========================================
# 2. 第一次调用：让模型识别论文信息
# =========================================

print("发送给模型识别...")

#建立函数映射表
availabel_functions={
    "paper_verify": paper_verify,
    "certificate_verify": certificate_verify
}

#存储每个文件的最终结论
all_final_answers=[]

for file_data in processed_files_data:
    print(f"\n{'='*50}\n处理文件 #{file_data['index']} (文件名: {file_data['filename']}) 的验证请求...")
    
    #为每个文件单独构建消息
    #file_messages=messages.copy()
    messages=[{
        "role":"user",
        "content":[
            {
                "type":"text",
                "text":f"请识别这个文件 #{file_data['index']} 的内容，并调用相应的验证工具（论文验证或学籍在线验证码验证）。"
            },
            {
                "type":"image_url",
                "image_url":{
                    "url":f"data:image/jpeg;base64,{file_data['base64_image']}"
                }
            }
        ]
    }]
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
    messages.append(assistant_message.model_dump())

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
        
            #核心逻辑，从映射表中获取函数并执行
            function_to_call = availabel_functions.get(function_name)

            if function_to_call:
                try:
                #使用**自动解包参数
                    result=function_to_call(**function_args)
                    print(f"验证结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
                # 将工具调用结果添加到消息历史
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result, ensure_ascii=False)
                    })
            
                except Exception as e:
                    print(f"调用工具时出错: {e}")
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps({
                        "status": "error",
                        "message": str(e)
                    }, ensure_ascii=False)
                    })
            
    # ==========================================
    # 4. 第二次调用：让模型根据验证结果给出回答
    # ==========================================
        # 强化指令：要求输出最终判定（验证通过/不通过）与简要理由
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "请根据工具返回结果，给出明确结论：\n对于论文验证：- 若工具返回 status=success，输出：验证通过，并简要说明匹配到的作者/DOI等依据。\n- 若工具返回 status=warning 或 failed，输出：验证不通过（或存在疑问），并简要说明原因。\n对于学籍在线验证报告或学历证书电子注册备案表验证：- 根据返回内容自行判断并简要说明原因。\n只输出中文结论与理由，尽量简洁。"
                }
            ]
        })

        final_response = client.chat.completions.create(
            model="GLM-4.6V-Flash",
            messages=messages
        )
    
        final_answer = final_response.choices[0].message.content
        all_final_answers.append(f"文件“{file_data['filename']}”：{final_answer}")
    else:
        # 如果模型没有调用工具，也记录下来
        final_answer = f"文件“{file_data['filename']}”：模型未调用任何工具进行验证，直接回复：{assistant_message.content}"
        all_final_answers.append(final_answer)

# ==========================================
# 最终汇总输出
# ==========================================
print(f"\n\n{'='*25} 最终验证结论汇总 {'='*25}")
for answer in all_final_answers:
    print(f"- {answer}")
print(f"{'='*70}")
