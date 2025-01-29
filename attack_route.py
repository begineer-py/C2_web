from flask import Blueprint, request, session, flash, redirect, url_for, jsonify, render_template, current_app, send_file, make_response
from models import Target, crawler, ParamSpiderResult
from thread_nmap import nmap_ScanThread
from reconnaissance.security_scanning.crtsh import crtsh_scan_target
from models import db, crtsh_Result
import time
from datetime import datetime
import queue
from thread_webtech import WebTechScanThread
from thread_paramspider import ParamSpiderThread
import json
import os
from flask_login import login_required, current_user
from utils.permission import check_user_permission 

# 創建一個藍圖，用於組織攻擊相關的路由
attack_bp = Blueprint('attack', __name__)


# 如果有使用cloudflare，則使用 FlareSolverr 掃描
@attack_bp.route('/user/<int:user_id>/flaresovlerr/<int:target_id>', methods=['POST'])
@login_required
def start_flaresolverr(user_id, target_id):
    # 檢查用戶權限
    permission_result = check_user_permission(current_user.id, target_id)
    if not isinstance(permission_result, Target):
        return permission_result
        
    target = permission_result
    return jsonify({'status': 'success', 'message': 'FlareSolverr 已啟動'}), 200






@attack_bp.route('/user/<int:user_id>/nmap/<int:target_id>', methods=['POST'])
@login_required
def nmap_scan(user_id, target_id):
    # 檢查用戶權限
    permission_result = check_user_permission(current_user.id, target_id)
    if not isinstance(permission_result, Target):
        return permission_result
        
    target = permission_result
    client_ip = request.remote_addr
    current_app.logger.debug(f"用戶 {current_user.id} 正在訪問 nmap 路由，目標 ID: {target_id} {client_ip}")
    
    try:
        # 創建並啟動掃描線程
        scan_thread = nmap_ScanThread(target.target_ip_no_https, current_user.id, target_id, current_app)
        scan_thread.start()
        current_app.logger.debug(f"掃描線程已啟動")
        
        # 等待結果（最多等待300秒）
        try:
            scan_result, success, code = scan_thread.get_result(timeout=300)
            if not success:
                raise Exception(scan_result if isinstance(scan_result, str) else "掃描失敗")
            
            if not scan_result or not isinstance(scan_result, dict):
                raise Exception("無效的掃描結果")
            
            current_app.logger.debug(f"掃描已完成")
            return jsonify({
                'status': 'success',
                'message': '掃描完成',
                'result': scan_result,
                'code': 200
            }), 200
            
        except queue.Empty:
            current_app.logger.error("掃描超時")
            return jsonify({
                'status': 'error',
                'message': '掃描超時，請稍後重試',
                'code': 408
            }), 408
        
    except Exception as e:
        error_msg = str(e)
        current_app.logger.error(f"Nmap scan error: {error_msg}")
        return jsonify({
            'status': 'error',
            'message': f'掃描過程中發生錯誤: {error_msg}',
            'code': 500
        }), 500

@attack_bp.route('/user/<int:user_id>/crtsh/<int:target_id>', methods=['POST'])
def crtsh(user_id, target_id):
    client_ip = request.remote_addr
    current_app.logger.debug(f"用戶 {user_id} 正在訪問 crtsh 路由，目標 ID: {target_id} {client_ip}")
    
    # 檢查用戶權限
    permission_result = check_user_permission(user_id, target_id)
    if not isinstance(permission_result, Target):
        return permission_result
        
    target = permission_result
    try:
        # 檢查是否已存在掃描結果
        existing_result = crtsh_Result.query.filter_by(
            target_id=target_id,
            user_id=user_id
        ).first()
        
        if existing_result:
            # 如果存在舊的結果，先刪除
            try:
                db.session.delete(existing_result)
                db.session.commit()
                current_app.logger.info(f"已刪除舊的掃描結果: target_id={target_id}")
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"刪除舊結果時發生錯誤: {str(e)}")
                
        # 執行掃描
        domains, success, message = crtsh_scan_target(target.target_ip_no_https, user_id, target_id)
        
        # 記錄域名數量
        current_app.logger.info(f"掃描完成，找到 {len(domains)} 個域名")
        
        # 驗證掃描結果
        if not isinstance(domains, list):
            current_app.logger.error("掃描結果格式無效：domains 不是列表類型")
            return jsonify({
                'status': 'error',
                'message': '掃描結果格式無效',
                'result': {
                    'domains': [],
                    'total': 0,
                    'scan_time': None,
                    'error_message': '返回的域名列表格式無效'
                },
                'code': 400
            }), 400
        
        # 創建新的掃描結果記錄
        scan_time = datetime.now()
        result = crtsh_Result(
            user_id=user_id,
            target_id=target_id,
            domains=domains,  # 這裡直接存儲域名列表
            total_domains=len(domains),  # 記錄總數
            status='success' if success else 'failed',
            error_message=None if success else message,
            scan_time=scan_time  # 記錄掃描時間
        )
        
        # 使用重試機制保存到數據庫
        max_retries = 3
        retry_count = 0
        while retry_count < max_retries:
            try:
                db.session.add(result)
                db.session.commit()
                current_app.logger.info(f"成功保存掃描結果到數據庫，包含 {len(domains)} 個域名")
                break
            except Exception as e:
                db.session.rollback()
                retry_count += 1
                if retry_count == max_retries:
                    current_app.logger.error(f"保存到數據庫失敗，已重試 {max_retries} 次: {str(e)}")
                    raise
                current_app.logger.warning(f"保存到數據庫時發生錯誤，正在重試 ({retry_count}/{max_retries}): {str(e)}")
                time.sleep(1)  # 等待1秒後重試
        
        # 返回響應
        response_data = {
            'status': 'success' if success else 'error',
            'message': '掃描完成' if success else message,
            'result': {
                'domains': domains,
                'total': len(domains),
                'scan_time': scan_time.timestamp(),
                'error_message': message if not success else None
            },
            'code': 200 if success else 400
        }
        
        return jsonify(response_data), 200 if success else 400
        
    except Exception as e:
        current_app.logger.error(f"crtsh 掃描過程中發生錯誤: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'掃描過程中發生錯誤: {str(e)}',
            'code': 500
        }), 500

@attack_bp.route('/user/<int:user_id>/webtech/<int:target_id>', methods=['POST'])
@login_required
def webtech_scan(user_id, target_id):
    try:
        current_app.logger.debug(f"用戶 {current_user.id} 正在訪問 webtech 路由，目標 ID: {target_id} {request.remote_addr}")
        
        # 檢查用戶權限
        permission_result = check_user_permission(current_user.id, target_id)
        if not isinstance(permission_result, Target):
            return permission_result
            
        target = permission_result
            
        # 创建扫描线程
        scan_thread = WebTechScanThread(
            app=current_app,
            target_ip=target.target_ip_no_https,
            user_id=current_user.id,
            target_id=target_id
        )
        
        # 启动扫描
        scan_thread.start()
        current_app.logger.debug("掃描線程已啟動")
        
        # 等待结果
        result, success, code = scan_thread.get_result(timeout=300)
        current_app.logger.debug("掃描已完成")
        
        if success:
            return jsonify({
                'status': 'success',
                'message': '掃描完成',
                'result': result,
                'code': code
            }), code
        else:
            current_app.logger.error(f"Webtech scan error: {result}")
            return jsonify({
                'status': 'error',
                'message': result,
                'code': code
            }), code
            
    except Exception as e:
        current_app.logger.error(f"Webtech scan error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': '掃描失敗',
            'code': 500
        }), 500

@attack_bp.route('/user/<int:user_id>/attack/<int:target_id>', methods=['GET'])
@login_required
def attack(user_id, target_id):
    # 檢查用戶權限
    permission_result = check_user_permission(current_user.id, target_id)
    if not isinstance(permission_result, Target):
        return permission_result
        
    target = permission_result
    
    # 渲染攻擊頁面
    current_app.logger.info(f"用戶 {current_user.id} 正在訪問攻擊頁面，目標 ID: {target_id}")
    return render_template('attack.html', target_id=target_id, target=target)

@attack_bp.route('/user/<int:user_id>/paramspider/<int:target_id>', methods=['POST'])
@login_required
def paramspider_scan(user_id, target_id):
    # 檢查用戶權限
    permission_result = check_user_permission(current_user.id, target_id)
    if not isinstance(permission_result, Target):
        return permission_result
        
    target = permission_result
    client_ip = request.remote_addr
    current_app.logger.debug(f"用戶 {current_user.id} 正在訪問 paramspider 路由，目標 ID: {target_id} {client_ip}")
    
    try:
        # 獲取掃描參數
        data = request.get_json() or {}
        exclude = data.get('exclude', '')
        threads = int(data.get('threads', 50))
        
        # 創建爬蟲記錄
        crawler_record = crawler(target_id=target_id)
        db.session.add(crawler_record)
        db.session.commit()
        
        # 創建並啟動掃描線程
        scan_thread = ParamSpiderThread(
            target_url=target.target_ip_no_https,
            target_id=target_id,
            user_id=current_user.id,
            crawler_id=crawler_record.id,
            app=current_app,
            exclude=exclude,
            threads=threads
        )
        scan_thread.start()
        current_app.logger.debug(f"掃描線程已啟動")
        
        # 等待結果（最多等待300秒）
        try:
            scan_result, success, code = scan_thread.get_result(timeout=300)
            if not success:
                raise Exception(scan_result if isinstance(scan_result, str) else "掃描失敗")
            
            current_app.logger.debug(f"掃描已完成")
            return jsonify({
                'status': 'success',
                'message': '掃描完成',
                'result': {
                    'result_text': scan_result['result_text'],
                    'total_urls': scan_result['total_urls'],
                    'unique_parameters': scan_result['unique_parameters']
                },
                'code': 200
            }), 200
            
        except queue.Empty:
            current_app.logger.error("掃描超時")
            return jsonify({
                'status': 'error',
                'message': '掃描超時，請稍後重試',
                'code': 408
            }), 408
        
    except Exception as e:
        error_msg = str(e)
        current_app.logger.error(f"ParamSpider scan error: {error_msg}")
        return jsonify({
            'status': 'error',
            'message': f'掃描過程中發生錯誤: {error_msg}',
            'code': 500
        }), 500

@attack_bp.route('/user/<int:user_id>/paramspider/<int:target_id>/download/<int:crawler_id>')
@login_required
def download_paramspider_result(user_id, target_id, crawler_id):
    # 檢查用戶權限
    permission_result = check_user_permission(user_id, target_id)
    if not isinstance(permission_result, Target):
        return permission_result
        
    try:
        # 從資料庫中獲取 ParamSpider 結果
        crawler = ParamSpiderResult.query.filter_by(
            id=crawler_id,
            target_id=target_id
        ).first()
        
        if not crawler:
            return jsonify({
                'status': 'error',
                'message': '找不到指定的掃描結果'
            }), 404
            
        # 檢查結果是否存在
        if not crawler.result_text:
            return jsonify({
                'status': 'error',
                'message': '掃描結果為空'
            }), 404
            
        # 創建臨時文件
        filename = f'paramspider_result_{crawler_id}.txt'
        response = make_response(crawler.result_text)
        response.headers['Content-Type'] = 'text/plain'
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
        
        return response
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'下載失敗: {str(e)}'
        }), 500

@attack_bp.route('/api/paramspider/latest/<int:target_id>')
@login_required
def get_latest_paramspider_result(target_id):
    """獲取最新的 ParamSpider 掃描結果"""
    try:
        # 檢查用戶權限
        target = check_user_permission(current_user.id, target_id)
        if not target:
            return jsonify({'status': 'error', 'message': '無權訪問該目標'}), 403
        
        # 獲取最新結果
        result = ParamSpiderResult.get_latest_by_target(target_id)
        if result:
            return jsonify({
                'status': 'success',
                'data': result.to_dict()
            })
        else:
            return jsonify({
                'status': 'error',
                'message': '未找到掃描結果'
            }), 404
            
    except Exception as e:
        current_app.logger.error(f"Error getting latest ParamSpider result: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': '獲取結果失敗'
        }), 500

@attack_bp.route('/api/paramspider/all/<int:target_id>')
@login_required
def get_all_paramspider_results(target_id):
    """獲取所有 ParamSpider 掃描結果"""
    try:
        # 檢查用戶權限
        target = check_user_permission(current_user.id, target_id)
        if not target:
            return jsonify({'status': 'error', 'message': '無權訪問該目標'}), 403
        
        # 獲取所有結果
        results = ParamSpiderResult.get_by_target_id(target_id)
        if results:
            return jsonify({
                'status': 'success',
                'data': [result.to_dict() for result in results]
            })
        else:
            return jsonify({
                'status': 'error',
                'message': '未找到掃描結果'
            }), 404
            
    except Exception as e:
        current_app.logger.error(f"Error getting all ParamSpider results: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': '獲取結果失敗'
        }), 500


