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
        err = traceback.format_exc()
        logger.exception("快速编辑出错")
        try:
            from tkinter import messagebox
            messagebox.showerror("FileNote 错误", f"快速编辑出错：\n\n{err}")
        except Exception:
            pass


def _do_quick_edit(target_path: str):
    import customtkinter as ctk
    from ui.manager import upsert_note, Toast
    from data.store import connect
    import sqlite3
    import markdown as md_lib

    ctk.set_appearance_mode("system")
    ctk.set_default_color_theme("blue")

    # 配色（与 manager.py 保持一致）
    COLOR_PRIMARY = "#6366F1"
    COLOR_PRIMARY_HOVER = "#4F46E5"
    COLOR_SUCCESS = "#10B981"
    COLOR_SUCCESS_HOVER = "#059669"
    COLOR_BG_SIDEBAR = ("#F1F5F9", "gray15")
    COLOR_TEXT_PRIMARY = ("gray15", "gray90")
    COLOR_TEXT_MUTED = ("gray55", "gray50")

    FONT_TITLE = ("微软雅黑", 18, "bold")
    FONT_NORMAL = ("微软雅黑", 13)
    FONT_SMALL = ("微软雅黑", 11)
    FONT_MONO = ("Cascadia Code", 12)
    FONT_ICON = ("Segoe UI Emoji", 16)

    # 查询现有备注
    existing_note = ""
    with connect() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM notes WHERE path=?",
                           (os.path.normpath(target_path),)).fetchone()
        if row:
            existing_note = row["note"]

    root = ctk.CTk()
    root.title("FileNote - 快速编辑")
    root.geometry("640x520")
    root.minsize(480, 380)
    root.attributes('-topmost', True)

    # ===== 顶部标题栏 =====
    header = ctk.CTkFrame(root, fg_color=COLOR_PRIMARY, corner_radius=0, height=60)
    header.pack(fill="x")
    header.pack_propagate(False)

    title_frame = ctk.CTkFrame(header, fg_color="transparent")
    title_frame.pack(fill="both", expand=True, padx=16)

    # 文件图标
    if os.path.isdir(target_path):
        icon = "📁"
    else:
        ext = os.path.splitext(target_path)[1].lower()
        icon_map = {".py": "🐍", ".js": "📜", ".ts": "📘", ".html": "🌐", ".css": "🎨",
                    ".md": "📝", ".txt": "📄", ".json": "📋", ".jpg": "🖼️", ".png": "🖼️",
                    ".pdf": "📕", ".doc": "📘", ".xls": "📊", ".zip": "📦"}
        icon = icon_map.get(ext, "📄")

    ctk.CTkLabel(title_frame, text=icon, font=FONT_ICON, text_color="white").pack(side="left", padx=(0, 8))
    name = os.path.basename(target_path) or target_path
    ctk.CTkLabel(title_frame, text=name, font=FONT_TITLE, text_color="white", anchor="w").pack(side="left", fill="x", expand=True)

    # ===== 路径栏 =====
    path_frame = ctk.CTkFrame(root, fg_color=COLOR_BG_SIDEBAR, corner_radius=0, height=36)
    path_frame.pack(fill="x")
    path_frame.pack_propagate(False)
    ctk.CTkLabel(path_frame, text=f"📍 {target_path}", font=FONT_SMALL, text_color=COLOR_TEXT_MUTED, anchor="w").pack(fill="both", padx=16, expand=True)

    # ===== 编辑/预览切换 =====
    tab_frame = ctk.CTkFrame(root, fg_color="transparent")
    tab_frame.pack(fill="x", padx=16, pady=(12, 4))

    editor_visible = [True]

    edit_tab_btn = ctk.CTkButton(tab_frame, text="✏️ 编辑", font=FONT_NORMAL, width=80, height=32,
                                  fg_color=COLOR_PRIMARY, hover_color=COLOR_PRIMARY_HOVER, corner_radius=8)
    edit_tab_btn.pack(side="left", padx=(0, 4))

    preview_tab_btn = ctk.CTkButton(tab_frame, text="👁️ 预览", font=FONT_NORMAL, width=80, height=32,
                                     fg_color="gray70", hover_color="gray60", corner_radius=8)
    preview_tab_btn.pack(side="left")

    # ===== 编辑器 =====
    editor = ctk.CTkTextbox(root, font=FONT_MONO, wrap="word", corner_radius=10, border_width=1)
    if existing_note:
        editor.insert("1.0", existing_note)
    editor.pack(fill="both", expand=True, padx=16, pady=(0, 8))

    # ===== 预览区 =====
    preview_frame = ctk.CTkFrame(root, fg_color="transparent")
    try:
        from tkinterweb import HtmlFrame
        html_frame = HtmlFrame(preview_frame, messages_enabled=False)
        html_frame.pack(fill="both", expand=True)
    except ImportError:
        html_frame = None
        ctk.CTkLabel(preview_frame, text="需要安装 tkinterweb：pip install tkinterweb",
                      font=FONT_NORMAL, text_color=COLOR_TEXT_MUTED).pack(expand=True)

    def switch_to_edit():
        editor_visible[0] = True
        preview_frame.pack_forget()
        editor.pack(fill="both", expand=True, padx=16, pady=(0, 8))
        edit_tab_btn.configure(fg_color=COLOR_PRIMARY)
        preview_tab_btn.configure(fg_color="gray70")

    def switch_to_preview():
        if not html_frame:
            Toast(root, "需要安装 tkinterweb", "warning")
            return
        editor_visible[0] = False
        editor.pack_forget()
        preview_frame.pack(fill="both", expand=True, padx=16, pady=(0, 8))
        edit_tab_btn.configure(fg_color="gray70")
        preview_tab_btn.configure(fg_color=COLOR_PRIMARY)

        md_text = editor.get("1.0", "end").strip()
        if not md_text:
            html_content = "<p style='color:gray;'>暂无内容</p>"
        else:
            html_content = md_lib.markdown(md_text, extensions=['fenced_code', 'tables', 'nl2br'])

        full_html = f"""<!DOCTYPE html><html><head><style>
        body {{ font-family: 'Microsoft YaHei UI', sans-serif; font-size: 14px; line-height: 1.8; color: #1f2937; padding: 16px; }}
        h1, h2, h3 {{ color: #111827; margin-top: 1.2em; }}
        h1 {{ font-size: 1.8em; border-bottom: 2px solid #e5e7eb; padding-bottom: 0.3em; }}
        h2 {{ font-size: 1.5em; border-bottom: 1px solid #e5e7eb; }}
        code {{ background: #f3f4f6; padding: 2px 6px; border-radius: 4px; font-family: 'Cascadia Code', monospace; }}
        pre {{ background: #1f2937; color: #f9fafb; padding: 16px; border-radius: 8px; overflow-x: auto; }}
        pre code {{ background: transparent; color: inherit; padding: 0; }}
        blockquote {{ border-left: 4px solid #6366f1; padding-left: 16px; color: #6b7280; }}
        a {{ color: #3b82f6; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #e5e7eb; padding: 8px 12px; }}
        th {{ background: #f9fafb; }}
        </style></head><body>{html_content}</body></html>"""
        html_frame.load_html(full_html)

    edit_tab_btn.configure(command=switch_to_edit)
    preview_tab_btn.configure(command=switch_to_preview)

    # ===== 底部按钮栏 =====
    btn_frame = ctk.CTkFrame(root, fg_color=COLOR_BG_SIDEBAR, corner_radius=0, height=56)
    btn_frame.pack(fill="x", side="bottom")
    btn_frame.pack_propagate(False)

    btn_inner = ctk.CTkFrame(btn_frame, fg_color="transparent")
    btn_inner.pack(fill="both", expand=True, padx=16)

    def save():
        note = editor.get("1.0", "end").strip()
        try:
            upsert_note(target_path, note)
            logger.info("备注已保存：{}", target_path)
            Toast(root, "备注已保存", "success")
            root.after(800, root.destroy)
        except Exception:
            logger.exception("保存失败")
            Toast(root, "保存失败", "error")

    def open_manager():
        root.destroy()
        launch_gui(target_path=target_path)

    ctk.CTkButton(btn_inner, text="📂 打开管理器", font=FONT_NORMAL, height=36, width=130,
                   fg_color="gray60", hover_color="gray50", corner_radius=8,
                   command=open_manager).pack(side="left")

    ctk.CTkButton(btn_inner, text="取消", font=FONT_NORMAL, height=36, width=80,
                   fg_color="gray60", hover_color="gray50", corner_radius=8,
                   command=root.destroy).pack(side="right", padx=(8, 0))
    ctk.CTkButton(btn_inner, text="💾 保存", font=FONT_NORMAL, height=36, width=100,
                   fg_color=COLOR_SUCCESS, hover_color=COLOR_SUCCESS_HOVER, corner_radius=8,
                   command=save).pack(side="right")

    # 快捷键
    root.bind("<Control-s>", lambda e: save())
    root.bind("<Escape>", lambda e: root.destroy())

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
