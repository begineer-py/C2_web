from flask import jsonify, current_app
from flask_login import current_user
from models import db, Target

def check_user_permission(user_id, target_id):
    """
    檢查用戶對目標的訪問權限
    
    Args:
        user_id: 用戶ID
        target_id: 目標ID
        
    Returns:
        Target 或 Response: 如果有權限返回目標對象，否則返回錯誤響應
    """
    try:
        if not current_user.is_authenticated:
            current_app.logger.warning(f"用戶未登入: user_id={user_id}")
            return jsonify({
                'status': 'error',
                'message': '請重新登入',
                'code': 401
            }), 401
            
        # 如果是管理員,允許訪問任何目標
        if current_user.is_admin:
            target = db.session.get(Target, target_id)
            if not target:
                current_app.logger.warning(f"目標不存在: target_id={target_id}")
                return jsonify({
                    'status': 'error',
                    'message': '目標不存在',
                    'code': 404
                }), 404
            return target
            
        # 非管理員需要檢查用戶ID匹配
        if current_user.id != user_id:
            current_app.logger.warning(f"用戶ID不匹配: session_id={current_user.id}, request_id={user_id}")
            return jsonify({
                'status': 'error',
                'message': '無權訪問',
                'code': 403
            }), 403
        
        # 獲取目標並檢查權限
        target = db.session.get(Target, target_id)
        
        if not target:
            current_app.logger.warning(f"目標不存在: target_id={target_id}")
            return jsonify({
                'status': 'error',
                'message': '目標不存在',
                'code': 404
            }), 404
            
        if target.user_id != current_user.id:
            current_app.logger.warning(f"無權訪問目標: user_id={user_id}, target_id={target_id}")
            return jsonify({
                'status': 'error',
                'message': '無權訪問該目標',
                'code': 403
            }), 403
            
        return target

    except Exception as e:
        current_app.logger.error(f"權限檢查過程中發生錯誤: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': '權限驗證失敗',
            'code': 500
        }), 500 