# app.py
from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash
from flask_sqlalchemy import SQLAlchemy
from utils.ai_check import check_reason_validity
from utils.doc_gen import generate_leave_doc
from flask import abort
from datetime import datetime  # 修改这行导入语句
import os
from dotenv import load_dotenv

load_dotenv()  # 加载.env文件中的环境变量

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI', 'sqlite:///leave.db')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')  # 从环境变量获取密钥
db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    password = db.Column(db.String(120))
    role = db.Column(db.String(20))


class LeaveRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer)
    reason = db.Column(db.String(500))
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='pending')
    ai_check = db.Column(db.String(20))
    teacher_comment = db.Column(db.String(500))
    attachment_path = db.Column(db.String(500))  # 新增附件路径字段


@app.route('/')
def home():
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and user.password == request.form['password']:
            session['user_id'] = user.id
            session['role'] = user.role
            # 根据角色重定向到不同页面
            return redirect(url_for('teacher_view' if user.role == 'teacher' else 'dashboard'))
        flash('用户名或密码错误')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/student', methods=['GET', 'POST'])
def dashboard():
    if 'role' not in session or session['role'] != 'student':
        return redirect(url_for('login'))

    if request.method == 'POST':
        # 处理文件上传
        file = request.files.get('attachment')
        file_path = None
        if file and file.filename:
            upload_folder = os.path.join(app.root_path, 'uploads')
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)
            filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
            file_path = os.path.join('uploads', filename)
            file.save(os.path.join(app.root_path, file_path))

        is_valid = check_reason_validity(request.form['reason'])
        new_request = LeaveRequest(
            student_id=session['user_id'],
            reason=request.form['reason'],
            start_date=datetime.strptime(request.form['start_date'], '%Y-%m-%d'),  # 移除多余的datetime
            end_date=datetime.strptime(request.form['end_date'], '%Y-%m-%d'),      # 移除多余的datetime
            ai_check='valid' if is_valid else 'invalid',
            attachment_path=file_path  # 保存附件路径
        )
        db.session.add(new_request)
        db.session.commit()

    requests = LeaveRequest.query.filter_by(student_id=session['user_id']).all()
    return render_template('student.html', requests=requests)


@app.route('/teacher')
def teacher_view():
    if 'role' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))

    requests = LeaveRequest.query.filter_by(status='pending').all()
    return render_template('teacher.html', requests=requests)


@app.route('/approve/<int:req_id>', methods=['GET', 'POST'])
def approve(req_id):
    req = LeaveRequest.query.get(req_id)
    if request.method == 'POST':
        req.status = 'approved'
        req.teacher_comment = request.form.get('comment', '')
        db.session.commit()
        return redirect(url_for('teacher_view'))
    return render_template('approve.html', request=req)

@app.route('/reject/<int:req_id>', methods=['GET', 'POST'])
def reject(req_id):
    req = LeaveRequest.query.get(req_id)
    if request.method == 'POST':
        req.status = 'rejected'
        req.teacher_comment = request.form.get('comment', '')
        db.session.commit()
        return redirect(url_for('teacher_view'))
    return render_template('reject.html', request=req)


@app.route('/download/<int:req_id>')
def download(req_id):
    req = LeaveRequest.query.get(req_id)
    if req.status != 'approved':
        abort(403, "请假申请尚未批准，无法下载假条")
    doc_path = generate_leave_doc(req)
    return send_file(doc_path, as_attachment=True)


@app.route('/download_attachment/<int:req_id>')
def download_attachment(req_id):
    req = LeaveRequest.query.get(req_id)
    if req.attachment_path:
        return send_file(os.path.join(app.root_path, req.attachment_path), as_attachment=True)
    abort(404)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # 初始化测试账号
        if not User.query.filter_by(username="teacher@test.com").first():
            teacher = User(
                username="teacher@test.com",
                password="654321",
                role="teacher"  # 修复缺少的逗号和闭合括号
            )
            db.session.add(teacher)
        if not User.query.filter_by(username="student@test.com").first():
            student = User(
                username="student@test.com",
                password="123456",
                role="student"
            )
            db.session.add(student)
        db.session.commit()
    app.run(host='0.0.0.0', port=5000)