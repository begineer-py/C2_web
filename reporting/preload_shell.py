import os
import subprocess
from control_reconnaissance import *

# 設置環境變數
os.environ['FLASK_APP'] = 'control_reconnaissance.py'
file_path = os.path.dirname(os.path.abspath(__file__))

# 可修改的部分
def show_modifiable_sections():
    print("\n=== 可修改的部分 ===")
    print("1. 添加鏈接: add_link('your_link_here')")
    print("2. 添加非 '.com' 鏈接: add_link_not_com('your_link_here')")
    print("3. 查詢 '.com' 鏈接: query_links_com()")
    print("4. 查詢非 '.com' 鏈接: query_links_not_com()")
    print("5. 刪除重複鏈接: remove_duplicates('LinksCom')")
    print("6. 刪除重複鏈接: remove_duplicates('LinksNotCom')")

# 顯示可修改部分
show_modifiable_sections()

# 手動創建 Flask 應用上下文
def main():
    with app.app_context():
        # 啟動 Flask Shell
        os.chdir(file_path)
        # 直接在這裡進行交互式命令輸入
        while True:
            command = input(">>> ")  # 等待用戶輸入命令
            if command.lower() in ['exit', 'quit']:
                break  # 終止循環
            try:
                # 使用 exec 執行命令
                exec(command)
            except Exception as e:
                print(f"執行命令時出錯: {e}")

if __name__ == "__main__":
    main()
