from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from models import User, Target, db
from flask_login import login_required, current_user

user_bp = Blueprint('user', __name__)

@user_bp.route('/dashboard/<int:user_id>', methods=['GET', 'POST'])
@login_required
def dashboard(user_id):
    # 檢查訪問權限
    if current_user.id != user_id and not current_user.is_admin:
        flash("無權訪問此頁面")
        return redirect(url_for('user.dashboard', user_id=current_user.id))
    
    # 渲染儀表盤頁面
    return render_template('dashboard.html')

@user_bp.route('/add_target', methods=['POST'])
@login_required
def add_target():
    # 獲取並驗證表單數據
    target_ip = request.form.get('target_ip')
    target_port = request.form.get('target_port')
    target_username = request.form.get('target_username')
    target_password = request.form.get('target_password')
    
    # 數據預處理
    if not all([target_ip, target_port, target_username, target_password]):
        flash("所有字段都是必需的")
        return redirect(url_for('user.dashboard', user_id=current_user.id))
    
    try:
        # 處理目標 IP
        target_ip_no_https = target_ip.replace('https://', '').replace('http://', '').replace("/","")
        
        # 創建新目標
        new_target = Target(
            target_ip=target_ip,
            target_port=int(target_port),
            target_username=target_username,
            target_password=target_password,
            target_ip_no_https=target_ip_no_https,
            user_id=current_user.id
        )
        
        # 保存到數據庫
        db.session.add(new_target)
        db.session.commit()
        flash("目標已添加")
        
    except ValueError:
        flash("端口必須是有效的數字")
    except Exception as e:
        db.session.rollback()
        flash(f"添加目標時出錯: {str(e)}")
    
    return redirect(url_for('user.dashboard', user_id=current_user.id))

@user_bp.route('/update_username', methods=['POST'])
@login_required
def update_username():
    # 獲取並驗證新用戶名
    new_username = request.form.get('new_username')
    if not new_username:
        flash("用戶名不能為空")
        return redirect(url_for('user.dashboard', user_id=current_user.id))
    
    # 檢查用戶名是否已存在
    if User.query.filter_by(username=new_username).first():
        flash("用戶名已存在")
    elif new_username == "admin":
        flash("用戶名不能為admin")
        return redirect(url_for('user.dashboard', user_id=current_user.id))
    
    try:
        # 更新用戶名
        current_user.username = new_username
        db.session.commit()
        flash("用戶名更新成功")
        
    except Exception as e:
        db.session.rollback()
        flash(f"更新用戶名時出錯: {str(e)}")
    
    return redirect(url_for('user.dashboard', user_id=current_user.id))
# 其他用戶相關的路由
