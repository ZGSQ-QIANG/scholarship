from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime

# ==================== 文件上传相关 ====================

class FileUploadResponse(BaseModel):
    """文件上传响应"""
    file_id: str
    filename: str
    message: str = "文件上传成功"

class SubmissionCreateResponse(BaseModel):
    """提交创建响应"""
    submission_id: str
    file_count: int
    message: str = "提交创建成功"

class ReplaceFileRequest(BaseModel):
    """替换提交中的文件"""
    old_file_id: str
    new_file_id: str
    filename: Optional[str] = None

# ==================== 验证相关 ====================

class VerifyResponse(BaseModel):
    """验证开始响应"""
    submission_id: str
    status: str
    message: str

class StatusResponse(BaseModel):
    """验证状态响应"""
    submission_id: str
    status: str  # processing, completed, failed
    progress: int  # 0-100
    current_step: str

class ToolResult(BaseModel):
    """工具调用结果"""
    tool_name: Optional[str] = None
    data: Optional[dict] = None
    
    class Config:
        extra = "allow"  # 允许额外字段

class FileResult(BaseModel):
    """单个文件的验证结果"""
    file_id: str
    filename: str
    verification_status: str  # success, warning, error
    ai_conclusion: Optional[str] = None
    tool_results: List[Any] = []  # 使用 Any 以接受任何格式的工具结果
    
    class Config:
        extra = "allow"

class FileVerificationResult(BaseModel):
    """文件验证结果（包含完整信息）"""
    file_id: str
    filename: str
    status: str  # success, warning, error
    result: FileResult

class ResultResponse(BaseModel):
    """验证结果响应"""
    submission_id: str
    status: str
    files: List[FileVerificationResult]