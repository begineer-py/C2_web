from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from flask_login import login_required, current_user
from models import User, db, Command_User

admin_bp = Blueprint('admin', __name__)

@admin_bp.route("/admin", methods=['GET', 'POST'])
@login_required
def admin():
    if not current_user.is_admin:
        flash("您沒有權限訪問此頁面")
        return redirect(url_for('index.login'))
        
    if request.method == 'GET':
        users = User.query.all()
        return render_template('admin.html', users=users)
        
    if request.method == 'POST':
        command = request.form.get('command')
        if command:
            new_command = Command_User(command=command)
            db.session.add(new_command)
            db.session.commit()
    return render_template('admin.html')

@admin_bp.route("/delete_user/<int:user_id>", methods=['POST'])
@login_required
def delete_user(user_id):
    if not current_user.is_admin:
        flash("您沒有權限執行此操作")
        return redirect(url_for('index.login'))
    
    try:
        user = User.query.get(user_id)
        if user:
            db.session.delete(user)
            db.session.commit()
            flash(f"用戶 {user.username} 已刪除")
        else:
            flash("用戶不存在")
    except Exception as e:
        db.session.rollback()
        flash(f"刪除用戶失敗: {str(e)}")
    
    return redirect(url_for('admin.admin')) 