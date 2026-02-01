from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json

Base = declarative_base()

class Submission(Base):
    """提交记录表"""
    __tablename__ = 'submissions'
    
    id = Column(String, primary_key=True)
    files_json = Column(Text)  # JSON 格式存储文件列表
    status = Column(String, default='pending')  # pending, processing, completed, failed
    progress = Column(Integer, default=0)
    current_step = Column(String, default='')
    results_json = Column(Text, nullable=True)  # JSON 格式存储验证结果
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'files': json.loads(self.files_json) if self.files_json else [],
            'status': self.status,
            'progress': self.progress,
            'current_step': self.current_step,
            'results': json.loads(self.results_json) if self.results_json else None,
            'error': self.error,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

# 创建数据库引擎（SQLite 文件）
engine = create_engine('sqlite:///./scholarship.db', echo=False, connect_args={"check_same_thread": False})

# 创建所有表
Base.metadata.create_all(engine)

# 创建会话工厂
SessionLocal = sessionmaker(bind=engine)

def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
