import threading
import time
from flask import current_app
from reconnaissance.security_scanning.webtech import webtech_scan_target
from models import db, webtech_Result
import json
from sqlalchemy.exc import OperationalError

class WebTechScanThread(threading.Thread):
    def __init__(self, app, target_ip, user_id, target_id):
        threading.Thread.__init__(self)
        self.app = app._get_current_object()  # 获取真实的 Flask 应用对象
        self.target_ip = target_ip
        self.user_id = user_id
        self.target_id = target_id
        self.result = None
        self.success = False
        self.code = 500
        self.daemon = True  # 设置为守护线程

    def run(self):
        try:
            # 在线程中创建应用上下文
            ctx = self.app.app_context()
            ctx.push()  # 推送上下文

            try:
                scan_result, success, code = webtech_scan_target(self.target_ip, self.user_id, self.target_id)
                self.result = scan_result
                self.success = success
                self.code = code

                if not success:
                    return

                # 检查现有结果
                existing_result = webtech_Result.query.filter_by(
                    target_id=self.target_id
                ).first()

                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        if existing_result:
                            # 将字典转换为JSON字符串
                            result_json = json.dumps(scan_result) if isinstance(scan_result, dict) else scan_result
                            existing_result.webtech_result = result_json
                        else:
                            # 将字典转换为JSON字符串
                            result_json = json.dumps(scan_result) if isinstance(scan_result, dict) else scan_result
                            new_result = webtech_Result(
                                user_id=self.user_id,
                                target_id=self.target_id,
                                webtech_result=result_json
                            )
                            db.session.add(new_result)
                        
                        db.session.commit()
                        break
                    except Exception as e:
                        db.session.rollback()
                        if attempt < max_retries - 1:
                            current_app.logger.warning(f"保存扫描结果时发生错误，尝试重试 {attempt + 1}/{max_retries}")
                            time.sleep(1)
                        else:
                            error_msg = f"扫描过程中发生错误: {str(e)}"
                            current_app.logger.error(error_msg)
                            self.result = error_msg
                            self.success = False
                            self.code = 500

            except Exception as e:
                error_msg = f"扫描过程中发生错误: {str(e)}"
                current_app.logger.error(error_msg)
                self.result = error_msg
                self.success = False
                self.code = 500
            finally:
                ctx.pop()  # 确保上下文被移除

        except Exception as e:
            self.result = f"应用上下文错误: {str(e)}"
            self.success = False
            self.code = 500

    def get_result(self, timeout=None):
        if timeout and self.is_alive():
            self.join(timeout=timeout)
            if self.is_alive():
                return {"error": "扫描超时"}, False, 408
        return self.result, self.success, self.code 