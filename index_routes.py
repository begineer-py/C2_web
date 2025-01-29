from flask import Blueprint, render_template,request,flash,redirect,url_for,session,request
from flask_login import login_user, logout_user, current_user
import os
from models import *
from datetime import datetime
index_bp = Blueprint('index', __name__)

@index_bp.route('/')
def index():
    if current_user.is_authenticated:  # 使用 Flask-Login 檢查登入狀態
        return redirect(url_for('user.dashboard', user_id=current_user.id))
    else:
        return render_template('index.html')

@index_bp.route('/favicon.ico')
def favicon():
    return  os.path.join(os.path.dirname(__file__), 'static', 'cake.jpg')# 返回圖片

@index_bp.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_name = request.form.get('username')
        password = request.form.get('password')
        try:
            user = User.query.filter_by(username=user_name).first()  # 查詢用戶
            if user_name == "admin" and password == "12345678":  # 管理員登入
                admin_user = User.query.filter_by(username="admin").first()
                if not admin_user:  # 如果管理員用戶不存在，創建一個
                    admin_user = User(username="admin", is_admin=True)
                    admin_user.set_password("12345678")
                    db.session.add(admin_user)
                    db.session.commit()
                login_user(admin_user)
                session['is_admin'] = True
                flash("登入成功")
                return redirect(url_for('admin.admin'))
            elif user is None:  # 用戶不存在
                flash("用戶不存在")
            elif not user.check_password(password):  # 密碼錯誤
                flash("密碼錯誤")
                return redirect(url_for('index.login'))
            else:  # 用戶登入
                login_user(user)
                session['is_admin'] = user.is_admin
                flash("登入成功")
                return redirect(url_for('user.dashboard', user_id=user.id))
        except Exception as e:
            flash(f"登入失敗: {str(e)}")
    return render_template('login.html')

@index_bp.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user_name = request.form.get('username')
        password = request.form.get('password')
        client_ip = request.remote_addr
        date = datetime.now()   
        try:
            if not user_name or not password:
                flash("註冊用戶和密碼不能為空")
            elif User.query.filter_by(username=user_name).first():
                flash("用戶已存在")
            elif len(user_name) > 20:
                flash("用戶名不能超過20個字")
            elif user_name == "admin":
                flash("用戶名不能為admin")
            elif len(password) < 8:
                flash("密碼不能少於8個字")
            else:
                user = User(username=user_name, registered_on=date, client_ip=client_ip)  # 不再需要 email
                user.set_password(password)  # 設置密碼哈希
                db.session.add(user)
                db.session.commit()
                flash("註冊成功")
                return redirect(url_for('index.login'))
        except Exception as e:
            flash(f"註冊失敗: {str(e)}")
    return render_template('register.html')  # 註冊頁面
@index_bp.route("/comment")
def comment():
    return render_template('comment.html')#留言頁面
@index_bp.route("/logout")
def logout():
    logout_user()  # 使用 Flask-Login 的 logout_user
    session.clear()
    return redirect(url_for('index.index'))
