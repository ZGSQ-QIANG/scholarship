# 奖学金材料验证系统

一个基于 AI 的奖学金申请材料自动验证系统，支持学术论文、学信网证明、专利证书的真实性验证。

## 技术栈

### 后端
- **FastAPI**: 高性能 Web 框架
- **SQLAlchemy**: ORM 数据库操作
- **ZhipuAI**: GLM-4V 多模态大模型
- **Playwright**: 自动化浏览器验证
- **SQLite**: 轻量级数据库

### 前端
- **Vue 3**: 渐进式 JavaScript 框架
- **Element Plus**: Vue 3 组件库
- **Vite**: 下一代前端构建工具
- **Axios**: HTTP 客户端

## 功能特性

✅ **多格式支持**: PDF、PNG、JPG、JPEG、BMP、WEBP  
✅ **智能识别**: AI 自动识别文件类型并选择验证策略  
✅ **三大验证工具**:
   - 学术论文验证（基于 CrossRef API）
   - 学信网学籍证明验证
   - 专利证书验证（中国知识产权局）  
✅ **实时状态**: 验证进度实时显示  
✅ **批量处理**: 支持多文件批量上传和验证  
✅ **详细报告**: 验证结果详情展示

## 项目结构

```
scholarship/
├── backend/                           # 🔧 后端服务（FastAPI）
│   ├── main.py                       # FastAPI 入口
│   ├── api/
│   │   ├── upload.py                 # 文件上传 API
│   │   └── verify.py                 # 验证 API
│   ├── services/
│   │   ├── verification_service.py   # 核心验证服务（重构的 main.py）
│   │   ├── paper_verify.py          # 论文验证
│   │   ├── certificate_verify.py    # 学信网验证
│   │   └── patent_verify.py         # 专利验证
│   ├── models/
│   │   ├── database.py              # 数据库连接与自动建表逻辑
│   │   └── schemas.py               # 数据模型
│   ├── utils/
│   │   └── image_processing.py      # 图片/PDF 处理
│   ├── tool_definitions.py          # AI 工具定义
│   └── requirements.txt             # Python 依赖
│ 
│
├── frontend/                          # 🎨 前端（Vue 3 + Vite）
│   ├── src/
│   │   ├── App.vue                  # 主应用
│   │   ├── main.js                  # 入口
│   │   ├── components/
│   │   │   ├── FileUpload.vue       # 文件上传组件（拖拽）
│   │   │   ├── SubmissionCard.vue   # 提交卡片（可折叠）
│   │   │   └── ResultCard.vue       # 结果卡片
│   │   ├── api/
│   │   │   └── client.js            # API 客户端
│   │   └── assets/
│   │       └── styles.css
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
└──

## 快速开始

### 1. 环境准备

确保已安装：
- Python 3.9+
- Node.js 16+
- npm 或 yarn

### 2. 克隆项目

```bash
cd scholarship
```

### 3. 配置环境变量

在项目根目录创建 `.env` 文件：

```env
ZHIPU_API_KEY=your_zhipu_api_key_here
DATABASE_URL=sqlite:///./scholarship_verification.db
```

### 4. 启动后端

```bash
# 进入后端目录
cd backend

# 安装 Python 依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install chromium

# 启动后端服务
python main.py
```

后端将运行在: `http://localhost:8000`  
API 文档: `http://localhost:8000/docs`

### 5. 启动前端

打开新的终端窗口：

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端将运行在: `http://localhost:3000`

### 6. 访问系统

在浏览器中打开 `http://localhost:3000`，即可使用系统。

## 使用说明

### 上传材料

1. 点击或拖拽文件到上传区域
2. 支持同时上传多个文件
3. 点击"上传"按钮

### 验证流程

1. 文件上传后自动进入验证队列
2. AI 识别文件内容（论文/证明/专利）
3. 调用相应的验证工具
4. 展示验证结果

### 结果说明

- **绿色（通过）**: 验证成功，材料真实有效
- **黄色（警告）**: 存在疑问，需人工复核
- **红色（失败）**: 验证失败，材料可能存在问题

## API 接口

### 上传文件
```http
POST /api/upload
Content-Type: multipart/form-data
```

### 触发验证
```http
POST /api/verify/{file_id}
```

### 获取结果
```http
GET /api/results/{file_id}
```

### 获取所有记录
```http
GET /api/results
```

## 开发说明

### 后端开发

- 使用 FastAPI 的 `BackgroundTasks` 处理耗时任务
- Playwright 同步函数在后台线程中运行
- SQLAlchemy 管理数据库会话

### 前端开发

- Vue 3 Composition API
- Element Plus 组件库
- 自动刷新验证状态（每3秒）

### 添加新的验证工具

1. 在 `services/` 目录添加验证函数
2. 在 `tool_definitions.py` 注册工具
