import os
from dotenv import load_dotenv
from zhipuai import ZhipuAI
from tool_definitions import tools_schema
from services.paper_verify import paper_verify
from services.certificate_verify import certificate_verify
from services.patent_verify import patent_verify
from utils.image_processing import process_pdf, process_image  # 修改这里
import json
import asyncio
from io import BytesIO

load_dotenv()

class VerificationService:
    def __init__(self):
        api_key = os.getenv("ZHIPU_API_KEY")
        if not api_key:
            raise ValueError("ZHIPU_API_KEY 未设置，请在 .env 文件中配置")
        self.client = ZhipuAI(api_key=api_key)
        self.available_functions = {
            "paper_verify": paper_verify,
            "certificate_verify": certificate_verify,
            "patent_verify": patent_verify
        }
    
    async def verify_files(self, files: list, status_callback=None):
        """验证多个文件"""
        results = []
        total = len(files)
        
        for index, file_info in enumerate(files, 1):
            if status_callback:
                status_callback(
                    progress=int((index - 1) / total * 100),
                    step=f"正在处理文件 {index}/{total}: {file_info['filename']}"
                )
            
            result = await self._verify_single_file(file_info, index, status_callback, total)
            results.append(result)
        
        return results
    
    async def _verify_single_file(self, file_info: dict, index: int, status_callback, total: int):
        """验证单个文件"""
        try:
            filename = file_info["filename"]
            file_id = file_info.get("file_id", "unknown")
            file_bytes = file_info["bytes"]
            ext = os.path.splitext(filename)[1].lower()
            
            # 处理文件
            if status_callback:
                status_callback(
                    progress=int((index - 0.7) / total * 100),
                    step=f"正在读取文件: {filename}"
                )
            
            if ext == '.pdf':
                base64_image = process_pdf(BytesIO(file_bytes))
            else:
                base64_image = process_image(BytesIO(file_bytes))
            
            # AI 识别
            if status_callback:
                status_callback(
                    progress=int((index - 0.5) / total * 100),
                    step=f"AI 正在识别: {filename}"
                )
            
            messages = [{
                "role": "system",
                "content": "你是一个专业的文件内容识别并验证助手。"
            },
                {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "请识别这个文件的内容，并调用相应的验证工具。"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }]
            
            response = self.client.chat.completions.create(
                model="GLM-4.6V-Flash",
                messages=messages,
                tools=tools_schema,
                tool_choice="auto"
            )
            
            assistant_message = response.choices[0].message

             # 🔍 添加调试日志
            print("=" * 50)
            print(f"文件: {filename}")
            print(f"AI 回复内容: {assistant_message.content}")
            print(f"是否有工具调用: {bool(assistant_message.tool_calls)}")
            if assistant_message.tool_calls:
                print(f"调用的工具: {[tc.function.name for tc in assistant_message.tool_calls]}")
            else:
                print("⚠️ AI 没有调用任何工具！")
            print("=" * 50)


            messages.append(assistant_message.model_dump())
            
            tool_results = []
            
            # 处理工具调用
            if assistant_message.tool_calls:
                if status_callback:
                    status_callback(
                        progress=int((index - 0.3) / total * 100),
                        step=f"正在验证: {filename}"
                    )
                
                for tool_call in assistant_message.tool_calls:
                    function_name = getattr(tool_call.function, "name", None)
                    function_args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
                    
                    if not function_name or function_name not in self.available_functions:
                        print(f"⚠️ 无效的工具名: {function_name}")
                        function_response = {
                            "status": "error",
                            "message": f"无效的工具名: {function_name}",
                            "verified": False
                        }
                    else:
                        # 调用函数
                        function_to_call = self.available_functions[function_name]
                        
                        # 处理异步函数
                        try:
                            if asyncio.iscoroutinefunction(function_to_call):
                                function_response = await function_to_call(**function_args)
                            else:
                                function_response = function_to_call(**function_args)
                                # 如果返回协程，补充 await
                                if asyncio.iscoroutine(function_response):
                                    function_response = await function_response
                        except Exception as tool_err:
                            print(f"⚠️ 工具 {function_name} 执行失败: {tool_err}")
                            function_response = {
                                "status": "error",
                                "message": f"工具执行异常: {str(tool_err)}",
                                "verified": False
                            }
                    
                    if function_response is None:
                        print(f"⚠️ 工具 {function_name} 返回了 None")
                        function_response = {
                            "status": "error",
                            "message": "工具执行未返回结果",
                            "verified": False
                        }

                    tool_results.append(function_response)
                    
                    # 添加工具结果
                    messages.append({
                        "role": "tool",
                        "content": json.dumps(function_response, ensure_ascii=False),
                        "tool_call_id": tool_call.id
                    })
                
                # 再次调用模型获取最终结论
                final_response = self.client.chat.completions.create(
                    model="GLM-4.6V-Flash",
                    messages=messages
                )
                
                final_answer = final_response.choices[0].message.content
                
                # 根据工具结果和AI结论判断真实状态
                verification_status = self._determine_status(tool_results, final_answer)
                
                print(f"✅ 验证完成: {filename}")
                print(f"   工具结果数: {len(tool_results)}")
                print(f"   最终状态: {verification_status}")
                
                return {
                    "file_id": file_id,
                    "filename": filename,
                    "status": verification_status,
                    "conclusion": final_answer,
                    "tool_results": tool_results
                }
            else:
                return {
                    "file_id": file_id,
                    "filename": filename,
                    "status": "warning",
                    "conclusion": assistant_message.content or "无法识别文件内容",
                    "tool_results": []
                }
        
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f"验证文件 {file_info.get('filename', 'unknown')} 时出错: {error_detail}")
            return {
                "file_id": file_info.get("file_id", "unknown"),
                "filename": file_info.get("filename", "unknown"),
                "status": "error",
                "conclusion": f"验证失败: {str(e)}",
                "tool_results": []
            }
    
    def _determine_status(self, tool_results: list, conclusion: str) -> str:
        """判断验证状态（修复版本）"""
        if not tool_results:
            return "error"
        
        # 检查工具结果
        has_error = False
        has_warning = False
        
        for result in tool_results:
            if isinstance(result, dict):
                # 检查 status 字段
                status = result.get("status", "").lower()
                verified = result.get("verified", None)
                
                # 如果明确标记为 error 或 verified=False
                if status == "error" or verified is False:
                    has_error = True
                elif status == "warning":
                    has_warning = True
                
                # 检查消息内容
                message = result.get("message", "").lower()
                if any(kw in message for kw in ["失败", "不存在", "错误", "无效", "不通过"]):
                    has_error = True
                elif any(kw in message for kw in ["警告", "无法确定", "建议"]):
                    has_warning = True
        
        # 检查 AI 结论
        conclusion_lower = conclusion.lower()
        if any(kw in conclusion_lower for kw in ["不真实", "伪造", "可疑", "失败", "不可信"]):
            has_error = True
        elif any(kw in conclusion_lower for kw in ["注意", "建议", "谨慎", "无法确定"]):
            has_warning = True
        
        # 优先级：error > warning > success
        if has_error:
            return "error"
        elif has_warning:
            return "warning"
        else:
            return "success"