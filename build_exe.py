"""
打包C盘清理工具为EXE文件
"""

import os
import shutil
import subprocess
import sys

APP_NAME = 'C盘清理工具'


def build_pyinstaller_command():
    """Build the PyInstaller command for the current platform."""
    add_data_separator = ';' if sys.platform.startswith('win') else ':'

    return [
        'pyinstaller',
        f'--name={APP_NAME}',
        '--onefile',
        '--windowed',
        '--icon=icons/cleaner.ico',
        f'--add-data=icons{add_data_separator}icons',
        '--noconfirm',
        '--clean',
        'main.py',
    ]


def build_exe():
    """使用PyInstaller打包应用为EXE文件"""
    print("开始打包C盘清理工具为EXE文件...")
    
    # 创建输出目录
    if not os.path.exists('dist'):
        os.makedirs('dist')
    
    # 清理旧的构建文件
    if os.path.exists('build'):
        shutil.rmtree('build')
    
    # 执行打包命令
    cmd = build_pyinstaller_command()
    subprocess.check_call(cmd)

    print("打包完成！")
    exe_path = os.path.abspath(os.path.join('dist', f'{APP_NAME}.exe'))
    print(f"EXE文件位于: {exe_path}")

    package_dir = os.path.join('dist', APP_NAME)
    os.makedirs(package_dir, exist_ok=True)

    if os.path.exists(exe_path):
        shutil.copy2(exe_path, os.path.join(package_dir, f'{APP_NAME}.exe'))

    # 创建启动批处理文件
    with open(os.path.join(package_dir, '启动C盘清理工具.bat'), 'w', encoding='utf-8') as f:
        f.write('@echo off\n')
        f.write('echo 正在启动C盘清理工具...\n')
        f.write('start "" "%~dp0C盘清理工具.exe"\n')
    
    print("已创建启动批处理文件")
    
    # 创建ZIP文件
    shutil.make_archive(APP_NAME, 'zip', package_dir)
    print(f"已创建ZIP文件: {os.path.abspath(f'{APP_NAME}.zip')}")

if __name__ == '__main__':
    build_exe()
