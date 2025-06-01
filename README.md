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