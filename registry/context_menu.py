"""
Windows 右键菜单注册/注销
在 HKEY_CLASSES_ROOT 中注册：
  *\\shell\\FileNote        -> 文件备注
  Directory\\shell\\FileNote -> 文件夹备注
"""

import sys
import os
import winreg
from loguru import logger

# 使用 __file__ 定位到项目根目录的 main.py（避免 sys.argv[0] 为 -c 的情况）
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_THIS_DIR)
SCRIPT_PATH = os.path.join(_PROJECT_ROOT, "main.py")
PYTHON_PATH = sys.executable

# 注册的菜单名称
MENU_NAME_FILE = "文件备注"
MENU_NAME_DIR = "文件夹备注"
# 用于管理器的命令：--gui "%1"
CMD = f'"{PYTHON_PATH}" "{SCRIPT_PATH}" --quick "%1"'
# 用于快速编辑弹窗的命令：--quick "%1"
CMD_QUICK = f'"{PYTHON_PATH}" "{SCRIPT_PATH}" --quick "%1"'


def register_context_menu() -> bool:
    """注册右键菜单（文件 + 文件夹）"""
    try:
        # --- 文件右键 ---
        key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, r'*\shell\FileNote')
        winreg.SetValueEx(key, '', 0, winreg.REG_SZ, MENU_NAME_FILE)
        # 设置图标（可选，指向 Python exe）
        winreg.SetValueEx(key, 'Icon', 0, winreg.REG_SZ, f'{PYTHON_PATH},0')

        cmd_key = winreg.CreateKey(key, 'command')
        winreg.SetValueEx(cmd_key, '', 0, winreg.REG_SZ, CMD)
        winreg.CloseKey(cmd_key)
        winreg.CloseKey(key)

        # --- 文件夹右键 ---
        dir_key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, r'Directory\shell\FileNote')
        winreg.SetValueEx(dir_key, '', 0, winreg.REG_SZ, MENU_NAME_DIR)
        winreg.SetValueEx(dir_key, 'Icon', 0, winreg.REG_SZ, f'{PYTHON_PATH},0')

        dir_cmd_key = winreg.CreateKey(dir_key, 'command')
        winreg.SetValueEx(dir_cmd_key, '', 0, winreg.REG_SZ, CMD)
        winreg.CloseKey(dir_cmd_key)
        winreg.CloseKey(dir_key)

        # --- 文件夹背景右键 ---
        bg_key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, r'Directory\Background\shell\FileNote')
        winreg.SetValueEx(bg_key, '', 0, winreg.REG_SZ, "在此处打开 FileNote")
        winreg.SetValueEx(bg_key, 'Icon', 0, winreg.REG_SZ, f'{PYTHON_PATH},0')

        bg_cmd_key = winreg.CreateKey(bg_key, 'command')
        winreg.SetValueEx(bg_cmd_key, '', 0, winreg.REG_SZ, f'"{PYTHON_PATH}" "{SCRIPT_PATH}" --gui')
        winreg.CloseKey(bg_cmd_key)
        winreg.CloseKey(bg_key)

        logger.info("右键菜单注册成功")
        return True
    except PermissionError:
        logger.error("注册失败：请以管理员身份运行")
        return False
    except Exception:
        logger.exception("注册右键菜单失败")
        return False


def unregister_context_menu() -> bool:
    """注销右键菜单"""
    try:
        # 删除文件右键
        try:
            winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, r'*\shell\FileNote\command')
            winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, r'*\shell\FileNote')
        except FileNotFoundError:
            pass

        # 删除文件夹右键
        try:
            winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, r'Directory\shell\FileNote\command')
            winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, r'Directory\shell\FileNote')
        except FileNotFoundError:
            pass

        # 删除文件夹背景右键
        try:
            winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, r'Directory\Background\shell\FileNote\command')
            winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, r'Directory\Background\shell\FileNote')
        except FileNotFoundError:
            pass

        logger.info("右键菜单注销成功")
        return True
    except Exception:
        logger.exception("注销右键菜单失败")
        return False
