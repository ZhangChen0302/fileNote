"""
FileNote 文件备注工具 - 统一入口
用法:
  python main.py                  -> 启动主窗口管理器
  python main.py --gui [path]     -> 启动管理器（可选定位到某路径）
  python main.py --quick <path>   -> 快速查看/编辑某文件备注弹窗
  python main.py --tray           -> 托盘常驻
  python main.py --register       -> 注册 Windows 右键菜单（需管理员）
  python main.py --unregister     -> 注销右键菜单（需管理员）
"""

import argparse
import sys
import os
from loguru import logger

# 确保脚本所在目录在 sys.path 中（从右键菜单启动时工作目录可能不是脚本目录）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
os.chdir(SCRIPT_DIR)

from data.store import init_db, migrate_json_if_needed


def launch_gui(target_path: str | None = None):
    """启动主窗口管理器"""
    from ui.manager import ManagerWindow
    try:
        logger.info("启动管理器，目标：{}", target_path or "无")
        app = ManagerWindow(target_path=target_path)
        app.mainloop()
    except Exception:
        logger.exception("启动管理器失败")
        raise


def launch_quick_edit(target_path: str):
    """快速查看/编辑指定路径的备注（右键菜单调用）"""
    import traceback
    try:
        _do_quick_edit(target_path)
    except Exception:
        # 错误时弹窗显示，避免窗口一闪而过看不到原因
        err = traceback.format_exc()
        logger.exception("快速编辑出错")
        try:
            from tkinter import messagebox
            messagebox.showerror("FileNote 错误", f"快速编辑出错：\n\n{err}")
        except Exception:
            pass


def _do_quick_edit(target_path: str):
    import customtkinter as ctk
    from ui.manager import upsert_note
    from data.store import connect
    import sqlite3

    ctk.set_appearance_mode("system")
    ctk.set_default_color_theme("blue")

    existing_note = ""
    with connect() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM notes WHERE path=?",
                           (os.path.normpath(target_path),)).fetchone()
        if row:
            existing_note = row["note"]

    root = ctk.CTk()
    root.title(f"备注 - {os.path.basename(target_path) or target_path}")
    root.geometry("560x420")
    root.minsize(400, 300)
    root.attributes('-topmost', True)

    ctk.CTkLabel(root, text=f"路径：{target_path}", font=("Microsoft YaHei UI", 11),
                 text_color="gray", anchor="w").pack(fill="x", padx=12, pady=(10, 2))

    editor = ctk.CTkTextbox(root, font=("Consolas", 13), wrap="word")
    editor.pack(fill="both", expand=True, padx=12, pady=8)
    if existing_note:
        editor.insert("1.0", existing_note)

    btn_frame = ctk.CTkFrame(root, fg_color="transparent")
    btn_frame.pack(fill="x", padx=12, pady=(0, 10))

    def save():
        note = editor.get("1.0", "end").strip()
        try:
            upsert_note(target_path, note)
            logger.info("备注已保存：{}", target_path)
            root.destroy()
        except Exception:
            logger.exception("保存失败")
            from tkinter import messagebox
            messagebox.showerror("错误", "保存失败")

    ctk.CTkButton(btn_frame, text="保存", font=("Microsoft YaHei UI", 13),
                   fg_color="#10B981", hover_color="#059669",
                   command=save).pack(side="right", padx=4)
    ctk.CTkButton(btn_frame, text="取消", font=("Microsoft YaHei UI", 13),
                   fg_color="gray", command=root.destroy).pack(side="right", padx=4)

    def open_manager():
        root.destroy()
        launch_gui(target_path=target_path)

    ctk.CTkButton(btn_frame, text="打开管理器", font=("Microsoft YaHei UI", 12),
                   command=open_manager).pack(side="left", padx=4)

    root.mainloop()


def launch_tray():
    """启动托盘（后续完善）"""
    logger.info("托盘功能待完善，先启动管理器")
    launch_gui()


def register_menu():
    from registry.context_menu import register_context_menu
    return register_context_menu()


def unregister_menu():
    from registry.context_menu import unregister_context_menu
    return unregister_context_menu()


def parse_args(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="FileNote 文件备注工具")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--gui", action="store_true", help="启动主窗口管理器")
    group.add_argument("--quick", action="store_true", help="快速查看/编辑某文件备注")
    group.add_argument("--tray", action="store_true", help="托盘常驻")
    group.add_argument("--register", action="store_true", help="注册右键菜单（需管理员）")
    group.add_argument("--unregister", action="store_true", help="注销右键菜单（需管理员）")
    parser.add_argument("target", nargs="?", default=None, help="目标文件/文件夹路径")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None):
    init_db()
    migrate_json_if_needed()

    args = parse_args(argv)

    if args.register:
        ok = register_menu()
        print("右键菜单注册成功" if ok else "右键菜单注册失败（请以管理员身份运行）")
        return 0 if ok else 1

    if args.unregister:
        ok = unregister_menu()
        print("右键菜单注销成功" if ok else "右键菜单注销失败")
        return 0 if ok else 1

    if args.quick:
        if not args.target:
            print("错误：--quick 需要指定目标路径")
            return 1
        launch_quick_edit(args.target)
        return 0

    if args.tray:
        launch_tray()
        return 0

    launch_gui(target_path=args.target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
