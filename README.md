# 学生请假管理系统

一个基于Flask的学生请假申请与审批系统，包含学生提交请假申请、教师审批、AI审核和统计功能。

## 功能特点

- **多角色登录**：学生和教师不同权限
- **请假申请**：学生可提交请假申请，支持附件上传
- **AI审核**：自动审核请假理由的真实性和合理性
- **审批流程**：教师可批准或拒绝请假申请
- **统计面板**：可视化展示请假数据统计
- **文档生成**：自动生成批准后的请假条文档

## 技术栈

- Python 3.x
- Flask 3.0.2
- Flask-SQLAlchemy 3.1.1
- Flask-Login 0.6.3
- DeepSeek API (AI审核)
- SQLite/MySQL (数据库)
- HTML/CSS/JavaScript (前端)

## 安装与运行

1. 克隆仓库
```bash
git clone https://github.com/GZXai/Student-Leave-Management-System
cd Student-Leave-Management-System

2.创建并激活虚拟环境 (Windows)
```bash
python -m venv venv
venv\Scripts\activate

3.安装依赖
```bash
pip install -r requirements.txt

4.配置环境变量
创建 .env 文件并配置：
```bash
DATABASE_URI=sqlite:///leave.db
SECRET_KEY=your_secret_key_here
DEEPSEEK_API_KEY=your_api_key_here

5.初始化数据库
```bash
flask shell
>>> from app import db
>>> db.create_all()
>>> exit()

6.运行应用
```bash
flask run


学生请假管理系统/
├── .gitignore
├── Dockerfile
├── README.md
├── app.py (主应用文件)
├── requirements.txt (依赖文件)
├── static/
│   └── style.css (前端样式文件)
├── templates/
│   ├── approve.html (审批页面)
│   ├── login.html (登录页面)
│   ├── reject.html (拒绝页面)
│   ├── student.html (学生页面)
│   ├── teacher.html (教师页面)
│   └── teacher_stats.html (统计页面)
└── utils/
    ├── ai_check.py (AI审核模块)
    └──  doc_gen.py (文档生成模块)
  
