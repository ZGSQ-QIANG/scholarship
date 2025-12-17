import os
import json
import base64
from io import BytesIO
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from zhipuai import ZhipuAI
from tool_definitions import tools_schema
from services.paper_verify import paper_verify
import fitz

load_dotenv()

app = Flask(__name__, static_folder='static')
CORS(app)

client = ZhipuAI(api_key=os.getenv("ZHIPU_API_KEY"))

# 用于存储会话历史
sessions = {}

def pdf_to_base64(file_bytes):
    """将PDF字节流转为第一页PNG的base64"""
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        page = doc.load_page(0)
        pix = page.get_pixmap(dpi=200)
        buffered = BytesIO(pix.tobytes("png"))
        encoded = base64.b64encode(buffered.getvalue()).decode("utf-8")
        doc.close()
        return encoded
    except Exception as e:
        raise RuntimeError(f"PDF渲染失败: {e}")

@app.route('/')
def index():
    """提供前端页面"""
    return send_from_directory('static', 'index.html')

@app.route('/upload', methods=['POST'])
def upload_paper():
    """处理PDF上传并触发论文验证"""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "未找到文件"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "文件名为空"}), 400
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({"error": "仅支持PDF格式"}), 400
        
        session_id = request.form.get('session_id', 'default')
        
        # 读取并转换PDF
        file_bytes = file.read()
        encoded_image = pdf_to_base64(file_bytes)
        
        # 初始化会话消息
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"文件：{file.filename}\n请识别这篇论文的关键信息，包括：标题、作者列表、DOI号（如果有）、发表日期。如果这是一篇学术论文，请调用论文验证工具进行验证。"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{encoded_image}"
                        }
                    }
                ]
            }
        ]
        
        # 首次调用模型
        response = client.chat.completions.create(
            model="GLM-4.6V-Flash",
            messages=messages,
            tools=tools_schema,
            tool_choice="auto"
        )
        
        assistant_message = response.choices[0].message
        messages.append(assistant_message.model_dump())
        
        # 处理工具调用
        tool_results = []
        if assistant_message.tool_calls:
            for tool_call in assistant_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                if function_name == "paper_verify":
                    result = paper_verify(
                        title=function_args.get("title"),
                        authors=function_args.get("authors"),
                        doi=function_args.get("doi")
                    )
                else:
                    result = {"error": "未知的工具"}
                
                tool_results.append(result)
                
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, ensure_ascii=False)
                })
            
            # 要求模型生成最终结论
            messages.append({
                "role": "user",
                "content": [{
                    "type": "text",
                    "text": "请根据工具返回结果，给出明确结论：\n- 若工具返回 status=success，输出：验证通过，并简要说明匹配到的作者/DOI等依据。\n- 若工具返回 status=warning 或 failed，输出：验证不通过（或存在疑问），并简要说明原因。\n只输出中文结论与理由，尽量简洁。"
                }]
            })
            
            final_response = client.chat.completions.create(
                model="GLM-4.6V-Flash",
                messages=messages
            )
            
            final_answer = final_response.choices[0].message.content
        else:
            final_answer = assistant_message.content
        
        # 保存会话历史
        sessions[session_id] = messages
        
        return jsonify({
            "success": True,
            "filename": file.filename,
            "answer": final_answer,
            "tool_results": tool_results
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat():
    """处理用户对话"""
    try:
        data = request.json
        user_message = data.get('message', '')
        session_id = data.get('session_id', 'default')
        
        if not user_message:
            return jsonify({"error": "消息不能为空"}), 400
        
        # 获取或初始化会话
        messages = sessions.get(session_id, [])
        
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        # 调用模型
        response = client.chat.completions.create(
            model="GLM-4.6V-Flash",
            messages=messages
        )
        
        assistant_reply = response.choices[0].message.content
        messages.append({
            "role": "assistant",
            "content": assistant_reply
        })
        
        # 更新会话
        sessions[session_id] = messages
        
        return jsonify({
            "success": True,
            "reply": assistant_reply
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/reset', methods=['POST'])
def reset_session():
    """重置会话"""
    data = request.json
    session_id = data.get('session_id', 'default')
    sessions[session_id] = []
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
