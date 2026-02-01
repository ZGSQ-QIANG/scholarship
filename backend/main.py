import sys
import os
from pathlib import Path

# 添加当前目录到 Python 路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import upload_router, verify_router

app = FastAPI(
    title="奖学金材料验证系统",
    description="基于 AI 的自动化验证系统",
    version="1.0.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(upload_router, prefix="/api", tags=["上传"])
app.include_router(verify_router, prefix="/api", tags=["验证"])

@app.get("/")
async def root():
    return {
        "message": "奖学金材料验证系统 API",
        "docs": "/docs",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    # 直接传递 app 对象，而不是字符串
    uvicorn.run(
        app,  # 这里改了！
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[str(current_dir)]
    )