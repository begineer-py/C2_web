import nmap
import json
from models import nmap_Result, db
from flask import current_app
from datetime import datetime
import time
from sqlalchemy.exc import OperationalError

def format_scan_result(scan_result, scan_time):
    try:
        # 檢查掃描結果
        if not scan_result or 'scan' not in scan_result or not scan_result['scan']:
            current_app.logger.error("Invalid scan result format")
            return {
                "host": "未知",
                "hostname": "未知",
                "state": "未知",
                "ports": {},
                "scan_time": scan_time
            }
        
        # 獲取主機信息
        host = list(scan_result['scan'].keys())[0]
        host_info = scan_result['scan'][host]
        
        # 獲取主機名
        hostname = "未知"
        if 'hostnames' in host_info and host_info['hostnames']:
            if isinstance(host_info['hostnames'], list):
                hostname = host_info['hostnames'][0].get('name', '未知')
            elif isinstance(host_info['hostnames'], dict):
                hostname = host_info['hostnames'].get('name', '未知')
        
        # 獲取主機狀態
        state = "未知"
        if 'status' in host_info:
            state = host_info['status'].get('state', '未知')
        
        # 格式化端口信息
        ports = {}
        if 'tcp' in host_info:
            for port_number, port_info in host_info['tcp'].items():
                ports[str(port_number)] = {
                    "state": port_info.get('state', 'unknown'),
                    "name": port_info.get('name', 'unknown'),
                    "product": port_info.get('product', ''),
                    "version": port_info.get('version', '')
                }
        
        # 構建結果字典
        result = {
            "host": host,
            "hostname": hostname,
            "state": state,
            "ports": ports,
            "scan_time": scan_time
        }
        
        current_app.logger.debug(f"Formatted scan result: {json.dumps(result)}")
        return result
        
    except Exception as e:
        current_app.logger.error(f"Error formatting scan result: {str(e)}")
        return {
            "host": "未知",
            "hostname": "未知",
            "state": "error",
            "ports": {},
            "scan_time": scan_time
        }

def nmap_scan_target(target_ip, target_id):
    try:
        # 移除 http:// 或 https:// 前綴，以及路徑和查詢參數
        target_ip_no_https = target_ip.replace('https://', '').replace('http://', '').split('/')[0].split('?')[0]
        
        # 記錄處理後的目標IP
        current_app.logger.debug(f"Processing target IP: {target_ip_no_https}")
        
        # 創建 nmap 掃描器實例
        nm = nmap.PortScanner()
        
        # 定義要掃描的端口列表
        ports = [21,22,23,25,53,80,110,143,443,465,587,993,995,1433,3306,3389,5900,6379,8080,8443,8888]
        ports_str = ','.join(map(str, ports))
        
        # 執行掃描，添加 -v 參數顯示詳細信息
        scan_result = nm.scan(
            target_ip_no_https, 
            arguments=f'-sS -sV -T4 -v -p{ports_str}'
        )
        
        # 獲取當前時間
        scan_time = datetime.now()
        
        # 格式化掃描結果
        formatted_result = format_scan_result(scan_result, scan_time.strftime("%Y-%m-%d %H:%M:%S"))
        
        # 確保所有掃描的端口都在結果中
        if 'ports' not in formatted_result:
            formatted_result['ports'] = {}
            
        for port in ports:
            port_str = str(port)
            if port_str not in formatted_result['ports']:
                formatted_result['ports'][port_str] = {
                    "state": "filtered",
                    "name": "unknown",
                    "product": "",
                    "version": ""
                }
        
        # 使用重試機制更新數據庫
        max_retries = 3
        retry_delay = 1  # 秒
        
        for attempt in range(max_retries):
            try:
                # 更新或創建數據庫記錄
                existing_result = nmap_Result.query.filter_by(target_id=target_id).first()
                
                if existing_result:
                    existing_result.scan_result = json.dumps(formatted_result)
                    existing_result.scan_time = scan_time
                else:
                    new_result = nmap_Result(
                        target_id=target_id,
                        scan_result=json.dumps(formatted_result),
                        scan_time=scan_time
                    )
                    db.session.add(new_result)
                
                db.session.commit()
                break  # 成功後跳出循環
                
            except OperationalError as e:
                if "database is locked" in str(e):
                    if attempt < max_retries - 1:
                        current_app.logger.warning(f"Database is locked, retrying... (attempt {attempt + 1}/{max_retries})")
                        db.session.rollback()
                        time.sleep(retry_delay)
                    else:
                        current_app.logger.error("Failed to update database after max retries")
                        raise
                else:
                    raise
            except Exception as e:
                db.session.rollback()
                raise
        
        return formatted_result, True, 200
        
    except Exception as e:
        current_app.logger.error(f"Nmap scan error: {str(e)}")
        error_result = {
            "host": target_ip_no_https,
            "hostname": "未知",
            "state": "error",
            "ports": {},
            "scan_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        current_app.logger.error(f"Nmap scan error: {str(e)}")
        return error_result, False, 500
