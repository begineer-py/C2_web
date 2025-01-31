import subprocess
import time
import json
import requests

def run_command(command):
    """執行命令並返回結果"""
    try:
        # 使用 cp950 編碼來處理中文 Windows 系統
        result = subprocess.run(
            command, 
            shell=True, 
            text=True, 
            capture_output=True, 
            encoding="cp950",
            errors="replace"
        )
        return result.returncode == 0, result.stdout.strip() if result.stdout else result.stderr.strip()
    except Exception as e:
        return False, str(e)

def check_docker_installed():
    """檢查是否安裝了 Docker"""
    success, _ = run_command("docker --version")
    return success

def start_docker_service():
    """啟動 Docker 服務"""
    print("正在啟動 Docker 服務...")
    # 使用 runas 以管理員權限執行命令
    commands = [
        'powershell -Command "Start-Process -FilePath \'net\' -ArgumentList \'start\', \'com.docker.service\' -Verb RunAs"',
        'powershell -Command "Start-Process -FilePath \'net\' -ArgumentList \'start\', \'Docker Desktop Service\' -Verb RunAs"'
    ]
    
    for cmd in commands:
        success, output = run_command(cmd)
        if success:
            print("Docker 服務啟動成功")
            return True
            
    print(f"Docker 服務啟動失敗，請確保以管理員權限運行程序")
    return False

def check_docker_running():
    """檢查 Docker 是否正在運行"""
    max_retries = 5
    retry_interval = 3
    
    print("正在檢查 Docker 引擎狀態...")
    for i in range(max_retries):
        success, output = run_command("docker info")
        if success:
            print("Docker 引擎運行正常")
            return True
        print(f"等待 Docker 引擎啟動... ({i + 1}/{max_retries})")
        time.sleep(retry_interval)
    
    print("Docker 引擎啟動失敗，請確保 Docker Desktop 已正確運行")
    return False

def check_flaresolverr_image():
    """檢查 FlareSolverr 映像是否存在"""
    success, output = run_command('docker images ghcr.io/flaresolverr/flaresolverr:latest --format "{{.Repository}}:{{.Tag}}"')
    return bool(output.strip())

def pull_flaresolverr_image():
    """拉取 FlareSolverr 映像"""
    print("正在拉取 FlareSolverr 映像...")
    success, output = run_command("docker pull ghcr.io/flaresolverr/flaresolverr:latest")
    if success:
        print("FlareSolverr 映像拉取成功")
        return True
    else:
        print(f"FlareSolverr 映像拉取失敗: {output}")
        return False

def check_container_exists(container_name="flaresolverr"):
    """檢查容器是否存在"""
    success, output = run_command(f'docker ps -a -q -f name={container_name}')
    return bool(output.strip())

def check_container_running(container_name="flaresolverr"):
    """檢查容器是否正在運行"""
    success, output = run_command(f'docker ps -q -f name={container_name} -f status=running')
    return bool(output.strip())

def get_container_logs(container_name="flaresolverr", tail=50):
    """獲取容器日誌"""
    success, output = run_command(f'docker logs --tail {tail} {container_name}')
    return output if success else ""

def check_flaresolverr_service():
    """檢查 FlareSolverr 服務是否響應"""
    try:
        # 使用 requests 庫來發送請求
        url = "http://localhost:8191/v1"
        headers = {"Content-Type": "application/json"}
        data = {"cmd": "sessions.create"}
        
        try:
            response = requests.post(url, json=data, headers=headers, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'ok' or result.get('message') == 'Session created successfully.':
                    print("FlareSolverr API 響應正常")
                    return True
                else:
                    print(f"服務響應異常: {result}")
            else:
                print(f"服務響應錯誤: HTTP {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"請求失敗: {str(e)}")
        return False
    except Exception as e:
        print(f"檢查服務時發生錯誤: {str(e)}")
        return False

def remove_container(container_name="flaresolverr"):
    """移除容器"""
    print(f"移除舊容器 {container_name}...")
    success, _ = run_command(f"docker stop {container_name}")
    if success:
        print(f"容器 {container_name} 已停止")
    success, _ = run_command(f"docker rm {container_name}")
    if success:
        print(f"容器 {container_name} 已移除")

def create_flaresolverr_container(container_name="flaresolverr"):
    """創建並運行 FlareSolverr 容器"""
    print("創建新的 FlareSolverr 容器...")
    
    # 先確保 Docker 引擎正常運行
    if not check_docker_running():
        return False
        
    command = (
        f"docker run -d --name {container_name} --restart unless-stopped "
        f"-p 8191:8191 -e LOG_LEVEL=info "
        f"ghcr.io/flaresolverr/flaresolverr:latest"
    )
    
    success, output = run_command(command)
    if success:
        print("FlareSolverr 容器創建成功")
        # 等待容器初始化
        time.sleep(5)
        return True
    else:
        print(f"容器創建失敗: {output}")
        # 如果失敗，檢查具體錯誤
        _, docker_error = run_command("docker ps -a")
        print(f"Docker 狀態: {docker_error}")
        return False

def wait_for_service(timeout=60):  # 增加超時時間到60秒
    """等待服務啟動"""
    print("等待 FlareSolverr 服務啟動...")
    start_time = time.time()
    check_interval = 2  # 每2秒檢查一次
    
    while time.time() - start_time < timeout:
        current_wait = int(time.time() - start_time)
        if check_flaresolverr_service():
            print("FlareSolverr 服務已成功啟動並響應正常")
            return True
            
        # 每10秒顯示一次容器日誌
        if current_wait % 10 == 0:
            logs = get_container_logs()
            if "Test successful!" in logs and "Serving on http://0.0.0.0:8191" in logs:
                print("容器日誌顯示服務已啟動，等待API響應...")
            print("\n最新容器日誌:")
            print(logs)
            
        print(f"等待服務啟動... ({current_wait}/{timeout}秒)")
        time.sleep(check_interval)
        
    print(f"\n服務啟動超時（{timeout}秒）")
    print("最終容器狀態:")
    success, status = run_command("docker ps --filter name=flaresolverr --format '{{.Status}}'")
    if success:
        print(f"容器狀態: {status}")
    print("\n最終容器日誌:")
    print(get_container_logs())
    return False

def start_flaresolverr():
    """確保 FlareSolverr 正在運行"""
    try:
        if not check_docker_installed():
            print("未檢測到 Docker，請先安裝 Docker Desktop")
            return False

        if not check_docker_running():
            print("Docker 未運行，嘗試啟動...")
            if not start_docker_service():
                return False
            # 給 Docker Desktop 一些時間完全啟動
            print("等待 Docker 服務完全啟動...")
            time.sleep(10)
            if not check_docker_running():
                print("Docker 引擎啟動失敗，請手動啟動 Docker Desktop")
                return False

        print("=== 檢查 FlareSolverr 容器狀態 ===")
        
        # 檢查映像是否存在
        if not check_flaresolverr_image():
            if not pull_flaresolverr_image():
                return False

        container_name = "flaresolverr"
        
        # 如果容器存在但未運行，嘗試啟動它
        if check_container_exists(container_name):
            if not check_container_running(container_name):
                print("容器存在但未運行，嘗試啟動...")
                success, _ = run_command(f"docker start {container_name}")
                if not success:
                    print("容器啟動失敗，嘗試移除並重新創建...")
                    run_command(f"docker rm -f {container_name}")
                    if not create_flaresolverr_container(container_name):
                        return False
        else:
            # 創建新容器
            if not create_flaresolverr_container(container_name):
                return False

        # 等待服務完全啟動
        return wait_for_service()
    except Exception as e:
        print(f"啟動 FlareSolverr 服務時發生錯誤: {str(e)}")
        return False

if __name__ == "__main__":
    start_flaresolverr()
