from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from typing import List
from sqlalchemy.orm import Session
import uuid
from datetime import datetime
import json

from models import FileUploadResponse, SubmissionCreateResponse
from models.schemas import ReplaceFileRequest
from models.database import get_db, Submission

# 文件临时存储（内存中，因为文件数据较大）
file_storage = {}  # {file_id: {"filename": str, "bytes": bytes, "uploaded_at": datetime}}

router = APIRouter()


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """
    上传单个文件
    
    支持的文件格式：PDF, PNG, JPG, JPEG, BMP, WEBP
    """
    # 验证文件类型
    allowed_extensions = {'.pdf', '.png', '.jpg', '.jpeg', '.bmp', '.webp'}
    file_ext = '.' + file.filename.split('.')[-1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"不支持的文件格式。支持的格式：{', '.join(allowed_extensions)}"
        )
    
    # 读取文件内容
    file_bytes = await file.read()
    
    # 生成唯一ID
    file_id = str(uuid.uuid4())
    
    # 存储文件
    file_storage[file_id] = {
        "filename": file.filename,
        "bytes": file_bytes,
        "uploaded_at": datetime.now()
    }
    
    return FileUploadResponse(
        file_id=file_id,
        filename=file.filename,
        message="文件上传成功"
    )


@router.post("/submissions", response_model=SubmissionCreateResponse)
async def create_submission(file_ids: List[str], db: Session = Depends(get_db)):
    """
    创建一个新的提交（包含多个文件）
    
    Args:
        file_ids: 文件ID列表
        db: 数据库会话
    """
    # 验证所有文件ID是否存在
    for file_id in file_ids:
        if file_id not in file_storage:
            raise HTTPException(status_code=404, detail=f"文件 {file_id} 不存在")
    
    # 生成提交ID
    submission_id = str(uuid.uuid4())
    
    # 准备文件信息
    files_info = []
    for file_id in file_ids:
        files_info.append({
            "file_id": file_id,
            "filename": file_storage[file_id]["filename"]
        })
    
    # 创建数据库记录
    submission = Submission(
        id=submission_id,
        files_json=json.dumps(files_info, ensure_ascii=False),
        status="pending",
        progress=0,
        current_step="等待验证..."
    )
    
    db.add(submission)
    db.commit()
    
    return SubmissionCreateResponse(
        submission_id=submission_id,
        file_count=len(file_ids),
        message="提交创建成功"
    )


@router.post("/submissions/{submission_id}/replace-file")
async def replace_submission_file(submission_id: str, payload: ReplaceFileRequest, db: Session = Depends(get_db)):
    """替换提交中的某个文件，并重置状态"""
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail=f"提交 {submission_id} 不存在")

    if payload.new_file_id not in file_storage:
        raise HTTPException(status_code=404, detail=f"文件 {payload.new_file_id} 不存在")

    files_info = json.loads(submission.files_json) if submission.files_json else []
    replaced = False
    for f in files_info:
        if f.get("file_id") == payload.old_file_id:
            f["file_id"] = payload.new_file_id
            f["filename"] = payload.filename or file_storage[payload.new_file_id]["filename"]
            replaced = True
            break

    if not replaced:
        raise HTTPException(status_code=404, detail=f"原文件 {payload.old_file_id} 不在该提交中")

    submission.files_json = json.dumps(files_info, ensure_ascii=False)
    submission.status = "pending"
    submission.progress = 0
    submission.current_step = "等待验证..."
    # 保留其他文件结果，仅移除被替换文件的旧结果
    if submission.results_json:
        try:
            existing_results = json.loads(submission.results_json)
            submission.results_json = json.dumps(
                [r for r in existing_results if r.get("file_id") != payload.old_file_id],
                ensure_ascii=False
            )
        except Exception:
            submission.results_json = None
    else:
        submission.results_json = None
    submission.error = None
    db.commit()

    return {
        "message": "文件替换成功",
        "submission_id": submission_id,
        "files": files_info
    }
