# app.py
from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash
from flask_sqlalchemy import SQLAlchemy
from utils.ai_check import check_reason_validity
from utils.doc_gen import generate_leave_doc
from flask import abort
from datetime import datetime
import os
import json  # 新增导入
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect
import time  # 新增导入


# 添加自定义过滤器
def fromjson_filter(value):
    return json.loads(value)


load_dotenv()  # 加载.env文件中的环境变量

app = Flask(__name__)
csrf = CSRFProtect(app)  # 将CSRF初始化移到正确位置
app.jinja_env.filters['fromjson'] = fromjson_filter
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI', 'sqlite:///leave.db')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')  # 从环境变量获取密钥
db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    password_hash = db.Column(db.String(256))  # 替换原来的password字段
    role = db.Column(db.String(20))
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class LeaveRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer)
    reason = db.Column(db.String(500))
    leave_type = db.Column(db.String(20))  # 新增请假类型字段
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='pending')
    ai_check = db.Column(db.String(20))
    teacher_comment = db.Column(db.String(500))
    attachment_path = db.Column(db.String(500))  # 新增附件路径字段
    ai_details = db.Column(db.Text)  # 新增字段存储AI审核详情


@app.route('/')
def home():
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and user.check_password(request.form['password']):  # 使用哈希验证
            session['user_id'] = user.id
            session['role'] = user.role
            return redirect(url_for('teacher_view' if user.role == 'teacher' else 'dashboard'))
        flash('用户名或密码错误')
        time.sleep(2)  # 增加延迟防止暴力破解
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
        file = request.files.get('attachment')
        file_path = None
        if file and file.filename:
            # 检查文件类型
            allowed_extensions = {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'}
            file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
            if file_ext not in allowed_extensions:
                flash('只允许上传PDF、Word文档或图片文件')
                return redirect(url_for('dashboard'))
                
            upload_folder = os.path.join(app.root_path, 'uploads')
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)
            filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
            file_path = os.path.join('uploads', filename)
            file.save(os.path.join(app.root_path, file_path))

        ai_result = check_reason_validity(request.form['reason'])
        new_request = LeaveRequest(
            student_id=session['user_id'],
            reason=request.form['reason'],
            leave_type=request.form['leave_type'],  # 新增请假类型
            start_date=datetime.strptime(request.form['start_date'], '%Y-%m-%d'),
            end_date=datetime.strptime(request.form['end_date'], '%Y-%m-%d'),
            ai_check='valid' if ai_result['is_valid'] else 'invalid',
            ai_details=json.dumps(ai_result['details']),
            attachment_path=file_path
        )
        db.session.add(new_request)
        db.session.commit()

    current_user = User.query.get(session['user_id'])
    requests = LeaveRequest.query.filter_by(student_id=session['user_id']).all()
    return render_template('student.html', requests=requests, student_id=current_user.id)


@app.route('/teacher')
def teacher_view():
    if 'role' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))

    search_name = request.args.get('search_name')
    if search_name:
        # 这里需要根据学生姓名查询，但当前模型只有student_id
        # 需要先建立学生姓名与ID的映射关系
        requests = LeaveRequest.query.filter_by(student_id=search_name).all()
    else:
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


@app.route('/teacher_stats')
def teacher_stats():
    if 'role' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))
    
    # 获取各种状态的请假数量
    pending_count = LeaveRequest.query.filter_by(status='pending').count()
    approved_count = LeaveRequest.query.filter_by(status='approved').count()
    rejected_count = LeaveRequest.query.filter_by(status='rejected').count()
    
    # 获取按请假类型统计的数据
    type_stats = db.session.query(
        LeaveRequest.leave_type,
        db.func.count(LeaveRequest.id)
    ).group_by(LeaveRequest.leave_type).all()
    
    # 获取按学生统计的数据
    student_stats = db.session.query(
        LeaveRequest.student_id,
        db.func.count(LeaveRequest.id)
    ).group_by(LeaveRequest.student_id).all()
    
    return render_template('teacher_stats.html', 
                         pending_count=pending_count,
                         approved_count=approved_count,
                         rejected_count=rejected_count,
                         type_stats=type_stats,
                         student_stats=student_stats)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username="teacher@test.com").first():
            teacher = User(
                username="teacher@test.com",
                role="teacher"
            )
            teacher.set_password("654321")
            db.session.add(teacher)
        if not User.query.filter_by(username="student@test.com").first():
            student = User(
                username="student@test.com",
                role="student"
            )
            student.set_password("123456")  # 修正为使用哈希密码
            db.session.add(student)
        if not User.query.filter_by(username="student2@test.com").first():
            student2 = User(
                username="student2@test.com",
                role="student"
            )
            student2.set_password("123456")  # 修正为使用哈希密码
            db.session.add(student2)
        db.session.commit()
    app.run(host='0.0.0.0', port=5000)