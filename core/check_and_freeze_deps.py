"""
依赖管理工具
用于检查、冻结和安装项目依赖
"""
import os
import sys
import subprocess
import pkg_resources
import argparse
from typing import List, Optional

CRITICAL_PACKAGES = {
    'watchdog': 'File monitoring',
    'tqdm': 'Progress bars',
    'requests': 'Network requests',
    'pydub': 'Audio processing',
}

def check_package_installed(package_name: str) -> bool:
    """检查包是否已安装"""
    try:
        pkg_resources.get_distribution(package_name)
        return True
    except pkg_resources.DistributionNotFound:
        return False

def get_package_version(package_name: str) -> Optional[str]:
    """获取已安装包的版本"""
    try:
        return pkg_resources.get_distribution(package_name).version
    except pkg_resources.DistributionNotFound:
        return None

def install_package(package_name: str) -> bool:
    """安装指定的包"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
        return True
    except subprocess.CalledProcessError:
        return False

def freeze_requirements(output_file: str = "requirements.txt"):
    """冻结当前环境的依赖到文件"""
    try:
        # 获取所有已安装的包
        installed = {pkg.key: pkg.version for pkg in pkg_resources.working_set}
        
        # 确保关键包被包含
        requirements = []
        for package, description in CRITICAL_PACKAGES.items():
            if package in installed:
                requirements.append(f"{package}>={installed[package]}")
            else:
                print(f"Warning: Critical package {package} ({description}) not found!")
        
        # 添加其他包
        for package, version in installed.items():
            if package not in CRITICAL_PACKAGES:
                requirements.append(f"{package}>={version}")
        
        # 写入文件
        with open(output_file, "w") as f:
            f.write("\n".join(sorted(requirements)))
            
        print(f"\nRequirements frozen to {output_file}")
        return True
        
    except Exception as e:
        print(f"Error freezing requirements: {str(e)}")
        return False

def install_requirements(requirements_file: str = "requirements.txt"):
    """从文件安装依赖"""
    if not os.path.exists(requirements_file):
        print(f"Requirements file {requirements_file} not found!")
        return False
        
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", requirements_file])
        print(f"\nRequirements installed from {requirements_file}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing requirements: {str(e)}")
        return False

def check_critical_packages() -> List[str]:
    """检查关键包是否已安装"""
    missing = []
    for package, description in CRITICAL_PACKAGES.items():
        if not check_package_installed(package):
            missing.append(package)
            print(f"Critical package missing: {package} ({description})")
    return missing

def main():
    parser = argparse.ArgumentParser(description="Dependency management tool")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # freeze命令
    freeze_parser = subparsers.add_parser("freeze", help="Freeze current environment")
    freeze_parser.add_argument("--file", default="requirements.txt", 
                             help="Output file (default: requirements.txt)")
    
    # install命令
    install_parser = subparsers.add_parser("install", help="Install from requirements")
    install_parser.add_argument("--file", default="requirements.txt",
                              help="Requirements file (default: requirements.txt)")
    
    # check命令
    subparsers.add_parser("check", help="Check critical packages")
    
    args = parser.parse_args()
    
    if args.command == "freeze":
        if freeze_requirements(args.file):
            sys.exit(0)
        sys.exit(1)
        
    elif args.command == "install":
        if install_requirements(args.file):
            sys.exit(0)
        sys.exit(1)
        
    elif args.command == "check":
        missing = check_critical_packages()
        if missing:
            print("\nSome critical packages are missing. Install them? [y/N]")
            if input().lower() == 'y':
                for package in missing:
                    print(f"\nInstalling {package}...")
                    if install_package(package):
                        print(f"{package} installed successfully")
                    else:
                        print(f"Failed to install {package}")
            sys.exit(len(missing))
        else:
            print("All critical packages are installed")
            sys.exit(0)
    
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
