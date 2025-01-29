import threading
from flask import current_app
from reconnaissance.security_scanning.crawler.crawler import crawler_scan_target

class CrawlerScanThread(threading.Thread):
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
                # crawler_scan_target 会处理所有数据库操作
                scan_result, success, code = crawler_scan_target(self.target_ip, self.user_id, self.target_id)
                self.result = scan_result
                self.success = success
                self.code = code

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