import os
import subprocess

def run_command(command):
    """運行命令行命令"""
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
    else:
        print(result.stdout)

def migrate_database():
    """自動遷移數據庫"""
    # 初始化遷移（如果需要）
    if not os.path.exists('migrations'):
        print("Initializing migrations...")
        run_command('flask db init')
    
    # 創建遷移腳本
    print("Creating migration script...")
    run_command('flask db migrate -m "Auto migration"')
    
    # 應用遷移
    print("Applying migration...")
    run_command('flask db upgrade')

if __name__ == "__main__":
    migrate_database()
