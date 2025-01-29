import threading
from queue import Queue
import time
from flask import current_app
from reconnaissance.curl_scanner.curl_scanner import scan_target_urls

class CurlScanThread(threading.Thread):
    def __init__(self, app, target_id):
        super().__init__()
        self.app = app
        self.target_id = target_id
        self.result_queue = Queue()
        self.daemon = True  # 設置為守護線程

    def run(self):
        """執行掃描線程"""
        try:
            with self.app.app_context():
                # 使用更新後的掃描函數
                result, success, code = scan_target_urls(self.target_id)
                self.result_queue.put((result, success, code))
        except Exception as e:
            self.app.logger.error(f"Curl掃描線程執行錯誤: {str(e)}")
            self.result_queue.put((str(e), False, 500))

    def get_result(self, timeout=None):
        """獲取掃描結果"""
        try:
            return self.result_queue.get(timeout=timeout)
        except Exception as e:
            self.app.logger.error(f"獲取Curl掃描結果時發生錯誤: {str(e)}")
            return str(e), False, 500 