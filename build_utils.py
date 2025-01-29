import os
import tempfile
import shutil
import logging
import PyInstaller.__main__

class BuildManager:
    def __init__(self):
        # 創建緩存目錄
        self.EXE_CACHE_DIR = os.path.join(tempfile.gettempdir(), 'optimizer_cache')
        self.TEMP_EXE_PATH = None  # 創建臨時 exe 路徑
        
    def create_exe(self):
        """將 Python 腳本打包成 exe 文件"""
        # 確定腳本的路徑
        script_path = os.path.join(os.path.dirname(__file__), "static", "system_optimizer.py")
        
        # 確保腳本文件存在
        if not os.path.exists(script_path):
            logging.error(f"腳本文件 {script_path} 不存在")
            return
        
        # 構建 exe 文件的路徑
        exe_path = os.path.join(os.path.dirname(__file__), "static", "system_optimizer.exe")
        
        # 檢查 .exe 文件是否已經存在
        if os.path.exists(exe_path):
            logging.error(f"已經存在 EXE 文件 {exe_path}")
            return
        
        try:
            # 執行 PyInstaller 打包命令
            PyInstaller.__main__.run([
                '--onefile',  # 單個文件打包
                '--noconsole',  # 不顯示控制台
                '--clean',  # 清理編譯過程
                '--name=system_optimizer',  # 設置 exe 名稱
                '--distpath=static',  # 設置輸出目錄
                '--log-level=INFO',  # 設置日誌級別
                '--add-data=*.py;.',  # 添加所有 py 文件到 exe
                script_path  # 傳遞 Python 腳本的完整路徑
            ])
            logging.info("成功生成 .exe 文件")
        except Exception as e:
            logging.error(f"創建 EXE 時出錯: {str(e)}")
