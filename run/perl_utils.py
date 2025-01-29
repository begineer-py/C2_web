import os
import subprocess
import sys

PERL_PATH = r"C:\Strawberry\perl\bin\perl.exe"

def check_perl_installation():
    """检查 Perl 是否安装"""
    if not os.path.exists(PERL_PATH):
        print(f"[!] 错误: Perl 可执行文件不存在: {PERL_PATH}")
        print("\n请执行以下步骤:")
        print("1. 下载 Strawberry Perl: https://strawberryperl.com/")
        print("2. 安装到默认位置: C:\\Strawberry")
        sys.exit(1)
    
    # 检查并安装必要的 Perl 模块
    if not check_perl_modules():
        print("[!] 错误: 无法安装必要的 Perl 模块")
        sys.exit(1)
        
    return PERL_PATH

def check_perl_modules():
    """检查并安装必要的 Perl 模块"""
    required_modules = [
        'Net::SSLeay',
        'IO::Socket::SSL',
        'LWP::UserAgent',
        'XML::LibXML'
    ]
    
    print("[*] 初始化 CPAN...")
    try:
        # 初始化 CPAN 配置
        subprocess.run([
            PERL_PATH,
            '-MCPAN',
            '-e',
            'CPAN::HandleConfig->load; CPAN::HandleConfig->edit("pushy_https", 0); CPAN::HandleConfig->commit'
        ], check=True)
        
        # 设置 CPAN 使用预编译包
        subprocess.run([
            PERL_PATH,
            '-MCPAN',
            '-e',
            'CPAN::HandleConfig->load; CPAN::HandleConfig->edit("prefer_installer", "MB"); CPAN::HandleConfig->edit("build_requires_install_policy", "yes"); CPAN::HandleConfig->commit'
        ], check=True)
        
        print("[+] CPAN 初始化完成")
    except subprocess.CalledProcessError as e:
        print(f"[-] CPAN 初始化失败: {e}")
        return False
    
    # 首先尝试安装 gcc 编译器
    try:
        print("[*] 检查 gcc 编译器...")
        gcc_check = subprocess.run(['gcc', '--version'], capture_output=True, text=True)
        if gcc_check.returncode != 0:
            print("[!] 未找到 gcc，尝试安装...")
            # 使用 Strawberry Perl 的包管理器安装 gcc
            subprocess.run([
                PERL_PATH,
                '-MCPAN',
                '-e',
                'install ExtUtils::MakeMaker'
            ], check=True)
    except:
        print("[!] gcc 检查失败，继续安装...")
    
    for module in required_modules:
        print(f"[*] 检查 Perl 模块: {module}")
        try:
            # 检查模块是否已安装
            result = subprocess.run(
                [PERL_PATH, '-M' + module, '-e', '1'],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"[!] 正在安装 {module}...")
                try:
                    # 使用预编译包安装
                    install_cmd = [
                        PERL_PATH,
                        '-MCPAN',
                        '-e',
                        f'CPAN::Shell->notest("install", "{module}");'
                    ]
                    subprocess.run(install_cmd, check=True)
                    
                    # 再次检查是否安装成功
                    check_result = subprocess.run(
                        [PERL_PATH, '-M' + module, '-e', '1'],
                        capture_output=True,
                        text=True
                    )
                    if check_result.returncode == 0:
                        print(f"[+] {module} 安装完成")
                    else:
                        print(f"[-] {module} 安装失败")
                        return False
                except subprocess.CalledProcessError as e:
                    print(f"[-] 安装失败: {e}")
                    return False
            else:
                print(f"[+] {module} 已安装")
                
        except subprocess.CalledProcessError as e:
            print(f"[-] 检查模块失败: {e}")
            return False
            
    return True 