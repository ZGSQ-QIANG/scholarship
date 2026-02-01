from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from sqlalchemy.orm import Session
from models.schemas import VerifyResponse, StatusResponse, ResultResponse, FileVerificationResult
from services.verification_service import VerificationService
from models.database import get_db, Submission
from api.upload import file_storage
import json

router = APIRouter()

# 验证服务实例
verification_service = VerificationService()

@router.post("/verify/{submission_id}", response_model=VerifyResponse)
async def start_verification(submission_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """开始验证流程"""
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail=f"提交 {submission_id} 不存在")

    # 防止重复验证
    if submission.status == "processing":
        return VerifyResponse(
            submission_id=submission_id,
            status=submission.status,
            message="验证已在进行中"
        )
    if submission.status == "completed" and submission.results_json:
        return VerifyResponse(
            submission_id=submission_id,
            status=submission.status,
            message="验证已完成"
        )
    
    # 更新状态为处理中
    submission.status = "processing"
    submission.progress = 0
    submission.current_step = "准备中..."
    db.commit()
    
    # 获取文件数据
    files_info = json.loads(submission.files_json)
    files_data = []
    for file_info in files_info:
        file_id = file_info["file_id"]
        if file_id in file_storage:
            files_data.append({
                "file_id": file_id,
                "filename": file_info["filename"],
                "bytes": file_storage[file_id]["bytes"]
            })
    
    # 后台任务
    background_tasks.add_task(run_verification, submission_id, files_data)
    
    return VerifyResponse(
        submission_id=submission_id,
        status="processing",
        message="验证已开始"
    )


@router.post("/verify/{submission_id}/file/{file_id}", response_model=VerifyResponse)
async def start_verification_for_file(submission_id: str, file_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """仅验证提交中的某一个文件"""
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail=f"提交 {submission_id} 不存在")

    files_info = json.loads(submission.files_json) if submission.files_json else []
    target = next((f for f in files_info if f.get("file_id") == file_id), None)
    if not target:
        raise HTTPException(status_code=404, detail=f"文件 {file_id} 不在该提交中")

    if file_id not in file_storage:
        raise HTTPException(status_code=404, detail=f"文件 {file_id} 不存在")

    # 更新状态为处理中
    submission.status = "processing"
    submission.progress = 0
    submission.current_step = f"正在验证文件: {target.get('filename', '')}"
    db.commit()

    files_data = [{
        "file_id": file_id,
        "filename": target.get("filename", ""),
        "bytes": file_storage[file_id]["bytes"]
    }]

    background_tasks.add_task(run_verification_for_file, submission_id, files_data)

    return VerifyResponse(
        submission_id=submission_id,
        status="processing",
        message="文件验证已开始"
    )

async def run_verification(submission_id: str, files: list):
    """后台执行验证"""
    # 创建新的数据库会话
    from models.database import SessionLocal
    db = SessionLocal()
    
    try:
        submission = db.query(Submission).filter(Submission.id == submission_id).first()
        if not submission:
            return
        
        def update_status(progress: int, step: str):
            """状态更新回调"""
            submission.progress = progress
            submission.current_step = step
            db.commit()
        
        # 调用验证服务
        results = await verification_service.verify_files(files, update_status)
        
        # 转换结果格式
        formatted_results = []
        for result in results:
            formatted_results.append({
                "file_id": result.get("file_id", ""),
                "filename": result.get("filename", ""),
                "status": result.get("status", "error"),
                "result": {
                    "file_id": result.get("file_id", ""),
                    "filename": result.get("filename", ""),
                    "verification_status": result.get("status", "error"),
                    "ai_conclusion": result.get("conclusion", ""),
                    "tool_results": result.get("tool_results", [])
                }
            })
        
        # 更新数据库记录
        submission.status = "completed"
        submission.progress = 100
        submission.current_step = "验证完成"
        submission.results_json = json.dumps(formatted_results, ensure_ascii=False)
        db.commit()
        
        print(f"✅ 验证完成: {submission_id}")
    
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"验证错误: {error_detail}")
        
        submission = db.query(Submission).filter(Submission.id == submission_id).first()
        if submission:
            submission.status = "failed"
            submission.progress = 0
            submission.current_step = f"错误: {str(e)}"
            submission.error = str(e)
            db.commit()
    
    finally:
        db.close()


async def run_verification_for_file(submission_id: str, files: list):
    """后台执行单文件验证并合并结果"""
    from models.database import SessionLocal
    db = SessionLocal()
    try:
        submission = db.query(Submission).filter(Submission.id == submission_id).first()
        if not submission:
            return

        def update_status(progress: int, step: str):
            submission.progress = progress
            submission.current_step = step
            db.commit()

        results = await verification_service.verify_files(files, update_status)

        # 格式化单文件结果
        formatted_results = []
        for result in results:
            formatted_results.append({
                "file_id": result.get("file_id", ""),
                "filename": result.get("filename", ""),
                "status": result.get("status", "error"),
                "result": {
                    "file_id": result.get("file_id", ""),
                    "filename": result.get("filename", ""),
                    "verification_status": result.get("status", "error"),
                    "ai_conclusion": result.get("conclusion", ""),
                    "tool_results": result.get("tool_results", [])
                }
            })

        # 合并结果
        existing = []
        if submission.results_json:
            try:
                existing = json.loads(submission.results_json)
            except Exception:
                existing = []

        result_map = {r.get("file_id"): r for r in existing if isinstance(r, dict)}
        for r in formatted_results:
            result_map[r.get("file_id")] = r

        submission.results_json = json.dumps(list(result_map.values()), ensure_ascii=False)
        submission.status = "completed"
        submission.progress = 100
        submission.current_step = "验证完成"
        db.commit()

        print(f"✅ 单文件验证完成: {submission_id}")
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"单文件验证错误: {error_detail}")
        submission = db.query(Submission).filter(Submission.id == submission_id).first()
        if submission:
            submission.status = "failed"
            submission.progress = 0
            submission.current_step = f"错误: {str(e)}"
            submission.error = str(e)
            db.commit()
    finally:
        db.close()

@router.get("/status/{submission_id}", response_model=StatusResponse)
async def get_status(submission_id: str, db: Session = Depends(get_db)):
    """查询验证状态"""
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="验证任务不存在")
    
    return StatusResponse(
        submission_id=submission_id,
        status=submission.status,
        progress=submission.progress,
        current_step=submission.current_step
    )

@router.get("/results/{submission_id}", response_model=ResultResponse)
async def get_results(submission_id: str, db: Session = Depends(get_db)):
    """获取验证结果"""
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="验证任务不存在")
    
    if submission.status != "completed":
        raise HTTPException(status_code=400, detail="验证尚未完成")
    
    # 解析结果
    files_results = json.loads(submission.results_json) if submission.results_json else []
    
    return ResultResponse(
        submission_id=submission_id,
        status=submission.status,
        files=files_results
    )

@router.get("/submissions", response_model=list)
async def get_all_submissions(db: Session = Depends(get_db), limit: int = 50):
    """获取所有提交记录（用于历史记录）"""
    submissions = db.query(Submission).order_by(Submission.created_at.desc()).limit(limit).all()
    
    results = []
    for sub in submissions:
        sub_dict = sub.to_dict()
        
        # 如果有结果，解析出来
        if sub.results_json:
            sub_dict['results'] = json.loads(sub.results_json)
        
        results.append(sub_dict)
    
    return results