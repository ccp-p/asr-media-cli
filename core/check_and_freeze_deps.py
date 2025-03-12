import subprocess
import sys
import importlib
import os

def check_installation(package):
    """检查包是否已安装"""
    try:
        importlib.import_module(package)
        return True
    except ImportError:
        return False

def get_package_version(package):
    """获取已安装包的版本"""
    try:
        return importlib.__import__(package).__version__
    except (ImportError, AttributeError):
        # 尝试使用pip方法获取版本
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'show', package],
                capture_output=True,
                text=True
            )
            for line in result.stdout.split('\n'):
                if line.startswith('Version:'):
                    return line.split(':', 1)[1].strip()
        except Exception:
            pass
        return "未知版本"

def freeze_dependencies(output_file='requirements.txt', ensure_packages=None):
    """
    冻结依赖并确保某些包被包含在内
    """
    if ensure_packages is None:
        ensure_packages = []
    
    # 获取pip freeze的输出
    result = subprocess.run(
        [sys.executable, '-m', 'pip', 'freeze'], 
        capture_output=True, 
        text=True
    )
    
    freeze_output = result.stdout.splitlines()
    freeze_packages = {line.split('==')[0].lower(): line for line in freeze_output if '==' in line}
    
    # 检查必需的包是否已存在于冻结列表中
    missing_packages = []
    for package in ensure_packages:
        if package.lower() not in freeze_packages:
            if check_installation(package):
                version = get_package_version(package)
                if version != "未知版本":
                    # 添加到冻结列表
                    freeze_packages[package.lower()] = f"{package}=={version}"
                else:
                    missing_packages.append(package)
            else:
                missing_packages.append(package)
    
    # 写入requirements文件
    with open(output_file, 'w') as f:
        for package_line in freeze_packages.values():
            f.write(f"{package_line}\n")
    
    print(f"依赖已写入 {output_file}")
    
    # 显示警告信息
    if missing_packages:
        print("\n警告: 以下包没有被包含在依赖列表中，可能需要手动安装:")
        for package in missing_packages:
            print(f" - {package}")
        print("\n你可以使用以下命令来安装这些包:")
        for package in missing_packages:
            print(f"pip install {package}")

if __name__ == "__main__":
    # 获取当前Python环境信息
    print(f"Python 版本: {sys.version}")
    print(f"Python 路径: {sys.executable}")
    
    # 检查watchdog是否已安装
    if check_installation('watchdog'):
        version = get_package_version('watchdog')
        print(f"watchdog已安装 (版本: {version})")
    else:
        print("警告: watchdog未安装在当前环境中")
        install_now = input("是否立即安装watchdog? (y/n): ")
        if install_now.lower() == 'y':
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'watchdog'])
            print("watchdog已安装")
    
    # 冻结依赖，确保包含watchdog
    freeze_dependencies(ensure_packages=['watchdog'])
