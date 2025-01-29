import threading
from queue import Queue, Empty
from reconnaissance.security_scanning.Scanner import nmap_scan_target

class nmap_ScanThread(threading.Thread):
    def __init__(self, target_ip, user_id, target_id, app):
        threading.Thread.__init__(self)
        self.target_ip = target_ip
        self.user_id = user_id
        self.target_id = target_id
        self.app = app._get_current_object()  # 获取真实的应用对象
        self.result = Queue()
        self.daemon = True

    def run(self):
        with self.app.app_context():  # 在线程中创建应用上下文
            try:
                scan_result, success, code = nmap_scan_target(self.target_ip, self.target_id)
                self.result.put((scan_result, success, code))
            except Exception as e:
                self.app.logger.error(f"Nmap scan thread error: {str(e)}")
                self.result.put((str(e), False, 500))

    def get_result(self, timeout=300):  # 默認超時時間設為5分鐘
        try:
            return self.result.get(timeout=timeout)
        except Empty:
            return None, False, 408  # 408 是超時狀態碼