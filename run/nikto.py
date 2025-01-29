from pathlib import Path
from datetime import datetime
import subprocess
from perl_utils import PERL_PATH
import sys
NIKTO_PATHS = [
    'nikto/program/nikto.pl',
    'tools/nikto/program/nikto.pl'
]

def test_port(domain, port, timeout=5):
    """測試端口是否可連接"""
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((domain, port))
        sock.close()
        return result == 0
    except Exception:
        return False

def run_nikto(domain, output_dir):
    """运行 Nikto 扫描"""
    print(f"\n[*] 开始 Nikto 扫描: {domain}")
    
    # 获取当前脚本的目录
    current_dir = Path(__file__).parent.resolve()
    base_dir = current_dir.parent
    
    # 检查所有可能的 Nikto 路径
    nikto_script = None
    for path in NIKTO_PATHS:
        test_path = base_dir / path
        if test_path.exists():
            nikto_script = test_path
            break
    
    if nikto_script is None:
        print(f"\n[-] 错误: 未找到 Nikto 脚本")
        print("[*] 已检查以下路径:")
        for path in NIKTO_PATHS:
            print(f"    - {base_dir / path}")
        return
    
    print(f"[+] 找到 Nikto 脚本: {nikto_script}")
    
    # 创建输出目录
    nikto_dir = output_dir / 'nikto'
    nikto_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n[*] 使用输出目录: {nikto_dir}")
    
    try:
        # 运行单次扫描，生成所有格式的报告
        output_base = str(nikto_dir / 'scan')
        
        # 尝试不同的端口
        ports_to_try = [80, 443, 8080, 8443]
        
        # 先测试哪些端口是开放的
        open_ports = []
        for port in ports_to_try:
            print(f"[*] 测试端口 {port}...")
            if test_port(domain, port):
                print(f"[+] 端口 {port} 开放")
                open_ports.append(port)
            else:
                print(f"[-] 端口 {port} 关闭或无法连接")
        
        if not open_ports:
            print(f"\n[-] 警告: 所有端口都无法连接")
            print(f"[*] 尝试的端口: {', '.join(map(str, ports_to_try))}")
            return
        
        print(f"\n[+] 发现开放端口: {', '.join(map(str, open_ports))}")
        
        for port in open_ports:
            print(f"\n[*] 扫描端口 {port}...")
            
            # 根据端口选择协议
            use_ssl = port in [443, 8443]
            
            scan_cmd = [
                PERL_PATH,
                str(nikto_script),
                '-h', f"{domain}",
                '-p', str(port),
                '-output', f"{output_base}_{port}.txt",
                '-Format', 'txt',
                '-Tuning', 'x',
                '-useragent', 'Mozilla/5.0',
                '-timeout', '10'
            ]
            
            # 根据端口添加或禁用 SSL
            if use_ssl:
                scan_cmd.extend(['-ssl'])
            else:
                scan_cmd.extend(['-nossl'])
            
            print(f"[*] 执行命令: {' '.join(scan_cmd)}")
            
            try:
                # 运行扫描并设置总体超时
                process = subprocess.Popen(
                    scan_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=str(nikto_script.parent),
                    bufsize=1,
                    universal_newlines=True
                )
                
                # 设置 10 分钟超时
                timeout = 600  # 10 minutes
                start_time = datetime.now()
                
                # 实时显示输出
                while True:
                    # 检查是否超时
                    if (datetime.now() - start_time).total_seconds() > timeout:
                        print(f"\n[-] 扫描超时，终止进程...")
                        process.terminate()
                        break
                    
                    # 读取输出
                    output = process.stdout.readline()
                    if output:
                        print(output.strip())
                    
                    error = process.stderr.readline()
                    if error:
                        print(f"[!] {error.strip()}", file=sys.stderr)
                    
                    # 检查进程是否结束
                    if output == '' and error == '' and process.poll() is not None:
                        break
                
                # 获取返回码
                return_code = process.poll()
                
                if return_code == 0:
                    print(f"\n[+] 端口 {port} 扫描完成")
                    
                    # 检查生成的文件
                    if Path(f"{output_base}_{port}.txt").exists():
                        print(f"[+] 成功生成报告: {output_base}_{port}.txt")
                        size = Path(f"{output_base}_{port}.txt").stat().st_size
                        print(f"    大小: {size} bytes")
                    else:
                        print(f"[-] 警告: 未找到输出文件 {output_base}_{port}.txt")
                else:
                    print(f"\n[-] 端口 {port} 扫描失败或超时")
                
            except subprocess.CalledProcessError as e:
                print(f"\n[-] 扫描失败: {e}")
                continue
            except KeyboardInterrupt:
                print("\n[!] 用户中断扫描")
                process.terminate()
                break
            
        # 创建扫描摘要
        summary_file = nikto_dir / 'summary.txt'
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(f"Nikto 扫描摘要\n{'='*30}\n\n")
            f.write(f"目标: {domain}\n")
            f.write(f"扫描时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Nikto 脚本: {nikto_script}\n\n")
            f.write("扫描结果:\n")
            
            for port in open_ports:
                f.write(f"\n端口 {port}:\n")
                report_file = Path(f"{output_base}_{port}.txt")
                if report_file.exists():
                    size = report_file.stat().st_size
                    f.write(f"- 文本报告: {size} bytes\n")
                else:
                    f.write("- 未生成报告\n")
        
        print(f"\n[+] 扫描摘要已保存到: {summary_file}")
        print("\n生成的文件:")
        for item in nikto_dir.iterdir():
            print(f"    - {item.name}")
            
    except Exception as e:
        print(f"\n[-] 发生错误: {e}")
        import traceback
        traceback.print_exc() 