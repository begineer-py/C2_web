import threading
from queue import Queue, Empty
from reconnaissance.paramspider.paramspider_scanner import ParamSpiderScanner

class ParamSpiderThread(threading.Thread):
    def __init__(self, target_url, target_id, user_id, crawler_id, app, exclude=None, threads=50):
        threading.Thread.__init__(self)
        self.target_url = target_url
        self.target_id = target_id
        self.user_id = user_id
        self.crawler_id = crawler_id
        self.app = app._get_current_object()
        self.exclude = exclude
        self.threads = threads
        self.result = Queue()
        self.daemon = True

    def run(self):
        with self.app.app_context():
            try:
                scanner = ParamSpiderScanner(
                    target_id=self.target_id,
                    user_id=self.user_id,
                    crawler_id=self.crawler_id,
                    exclude=self.exclude,
                    threads=self.threads
                )
                scan_result = scanner.scan(self.target_url)
                
                # 检查扫描结果的格式
                if isinstance(scan_result, dict):
                    if scan_result.get('status') == 'success':
                        self.result.put((scan_result, True, 200))
                    else:
                        error_msg = scan_result.get('message', '未知错误')
                        self.result.put((scan_result, False, 500))
                else:
                    self.app.logger.error(f"Invalid scan result format: {scan_result}")
                    self.result.put(({'status': 'error', 'message': '扫描结果格式无效'}, False, 500))
                    
            except Exception as e:
                self.app.logger.error(f"ParamSpider scan thread error: {str(e)}")
                self.result.put(({'status': 'error', 'message': str(e)}, False, 500))

    def get_result(self, timeout=300):
        """获取扫描结果，确保返回三个值：(result, success, code)"""
        try:
            result = self.result.get(timeout=timeout)
            if not isinstance(result, tuple) or len(result) != 3:
                self.app.logger.error(f"Invalid result format: {result}")
                return {'status': 'error', 'message': '结果格式无效'}, False, 500
            return result
        except Empty:
            return {'status': 'error', 'message': '扫描超时'}, False, 408
        except Exception as e:
            self.app.logger.error(f"Error getting result: {str(e)}")
            return {'status': 'error', 'message': str(e)}, False, 500 