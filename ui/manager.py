"""
FileNote 主窗口管理器
- 左侧：导航栏（带图标、高亮选中）
- 中间：卡片式备注列表（搜索/筛选/排序）
- 右侧：详情面板（Markdown 编辑/预览）
"""

import os
import sqlite3
import datetime as dt
import customtkinter as ctk
from tkinter import messagebox, Menu
from loguru import logger
from data.store import connect, _now
import markdown

# ============================================================
# 视觉常量
# ============================================================
FONT_TITLE = ("Microsoft YaHei UI", 22, "bold")
FONT_SUBTITLE = ("Microsoft YaHei UI", 15, "bold")
FONT_NORMAL = ("Microsoft YaHei UI", 13)
FONT_SMALL = ("Microsoft YaHei UI", 11)
FONT_MONO = ("Ubuntu Mono", 14)
FONT_ICON = ("Segoe UI Emoji", 16)

COLOR_PRIMARY = "#6366F1"
COLOR_PRIMARY_HOVER = "#4F46E5"
COLOR_SUCCESS = "#10B981"
COLOR_SUCCESS_HOVER = "#059669"
COLOR_WARN = "#F59E0B"
COLOR_WARN_HOVER = "#D97706"
COLOR_DANGER = "#EF4444"
COLOR_DANGER_HOVER = "#DC2626"
COLOR_INFO = "#3B82F6"

COLOR_TEXT_PRIMARY = ("gray15", "gray90")
COLOR_TEXT_SECONDARY = ("gray40", "gray60")
COLOR_TEXT_MUTED = ("gray55", "gray50")
COLOR_BORDER = ("gray80", "gray30")
COLOR_BG_CARD = ("white", "gray20")
COLOR_BG_CARD_HOVER = ("#F8FAFC", "gray25")
COLOR_BG_SELECTED = ("#EEF2FF", "#1E1B4B")
COLOR_BG_SIDEBAR = ("#F1F5F9", "gray15")
COLOR_BG_MAIN = ("#F8FAFC", "gray13")

# ============================================================
# 文件元数据工具
# ============================================================
def get_file_times(path: str) -> dict:
    try:
        stat = os.stat(path)
        return {
            "file_created": dt.datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M"),
            "file_modified": dt.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
            "file_size": stat.st_size,
        }
    except (OSError, ValueError):
        return {"file_created": "N/A", "file_modified": "N/A", "file_size": 0}


def get_file_type(path: str) -> str:
    if os.path.isdir(path):
        return "文件夹"
    ext = os.path.splitext(path)[1].lower()
    type_map = {
        ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
        ".html": "HTML", ".css": "CSS", ".json": "JSON", ".xml": "XML",
        ".md": "Markdown", ".txt": "文本", ".doc": "Word", ".docx": "Word",
        ".pdf": "PDF", ".xls": "Excel", ".xlsx": "Excel",
        ".ppt": "PowerPoint", ".pptx": "PowerPoint",
        ".jpg": "图片", ".jpeg": "图片", ".png": "图片", ".gif": "图片",
        ".svg": "图片", ".bmp": "图片", ".webp": "图片", ".ico": "图片",
        ".mp4": "视频", ".avi": "视频", ".mkv": "视频", ".mov": "视频",
        ".mp3": "音频", ".wav": "音频", ".flac": "音频", ".aac": "音频",
        ".zip": "压缩包", ".rar": "压缩包", ".7z": "压缩包",
        ".exe": "程序", ".bat": "脚本", ".sh": "脚本", ".cmd": "脚本",
        ".c": "C/C++", ".cpp": "C/C++", ".h": "C/C++",
        ".java": "Java", ".go": "Go", ".rs": "Rust", ".rb": "Ruby", ".php": "PHP",
    }
    return type_map.get(ext, ext.upper().lstrip(".") or "未知")


def get_file_type_icon(path: str) -> str:
    if os.path.isdir(path):
        return "📁"
    ext = os.path.splitext(path)[1].lower()
    icon_map = {
        ".py": "🐍", ".js": "📜", ".ts": "📘", ".html": "🌐", ".css": "🎨",
        ".md": "📝", ".txt": "📄", ".json": "📋", ".xml": "📰",
        ".jpg": "🖼", ".jpeg": "🖼", ".png": "🖼", ".gif": "🖼", ".svg": "🖼",
        ".bmp": "🖼", ".webp": "🖼", ".ico": "🖼",
        ".pdf": "📕", ".doc": "📘", ".docx": "📘", ".xls": "📊", ".xlsx": "📊",
        ".ppt": "📙", ".pptx": "📙",
        ".zip": "📦", ".rar": "📦", ".7z": "📦",
        ".exe": "⚙", ".bat": "⚙", ".sh": "⚙", ".cmd": "⚙",
        ".mp3": "🎵", ".mp4": "🎬", ".wav": "🎵", ".avi": "🎬", ".mkv": "🎬",
        ".c": "🔧", ".cpp": "🔧", ".h": "🔧", ".java": "☕", ".go": "🔵",
        ".rs": "🦀", ".swift": "🍎", ".kt": "🟣", ".rb": "💎", ".php": "🐘",
    }
    return icon_map.get(ext, "📄")


# ============================================================
# 数据操作
# ============================================================
def fetch_notes(keyword: str = "", tag: str | None = None,
                only_pinned: bool = False, only_fav: bool = False,
                only_folder: bool = False,
                file_type_exts: list[str] | None = None,
                sort_by: str = "updated_at", sort_desc: bool = True,
                limit: int = 500) -> list[dict]:
    sql = "SELECT id, path, note, pinned, favorite, created_at, updated_at FROM notes WHERE 1=1"
    params: list = []
    if keyword:
        sql += " AND (path LIKE ? OR note LIKE ?)"
        kw = f"%{keyword}%"
        params += [kw, kw]
    if only_pinned:
        sql += " AND pinned=1"
    if only_fav:
        sql += " AND favorite=1"
    if tag:
        sql += " AND id IN (SELECT note_id FROM note_tags JOIN tags ON tags.id=note_tags.tag_id WHERE tags.name=?)"
        params.append(tag)

    # 排序
    sort_map = {
        "updated_at": "updated_at",
        "created_at": "created_at",
        "path": "path",
    }
    order_col = sort_map.get(sort_by, "updated_at")
    order_dir = "DESC" if sort_desc else "ASC"
    sql += f" ORDER BY pinned DESC, {order_col} {order_dir} LIMIT ?"
    params.append(limit)

    with connect() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(sql, params).fetchall()
    results = [dict(r) for r in rows]

    # Python 端筛选
    if only_folder:
        results = [r for r in results if os.path.isdir(r["path"])]
    if file_type_exts:
        results = [r for r in results if any(r["path"].lower().endswith(ext) for ext in file_type_exts)]

    # 文件时间排序
    if sort_by in ("file_created", "file_modified"):
        def get_sort_key(item):
            try:
                stat = os.stat(item["path"])
                return stat.st_ctime if sort_by == "file_created" else stat.st_mtime
            except:
                return 0
        results.sort(key=get_sort_key, reverse=sort_desc)

    return results[:limit]


def fetch_tags() -> list[str]:
    with connect() as conn:
        rows = conn.execute("SELECT name FROM tags ORDER BY name").fetchall()
    return [r[0] for r in rows]


def upsert_note(path: str, note: str, pinned: int = 0, favorite: int = 0):
    ts = _now()
    with connect() as conn:
        conn.execute(
            """INSERT INTO notes(path, note, pinned, favorite, created_at, updated_at)
               VALUES(?, ?, ?, ?, ?, ?)
               ON CONFLICT(path) DO UPDATE SET note=excluded.note,
                   pinned=excluded.pinned, favorite=excluded.favorite, updated_at=excluded.updated_at""",
            (os.path.normpath(path), note, pinned, favorite, ts, ts),
        )


def delete_note_by_id(note_id: int):
    with connect() as conn:
        conn.execute("DELETE FROM notes WHERE id=?", (note_id,))


def toggle_pin(note_id: int):
    with connect() as conn:
        conn.execute("UPDATE notes SET pinned = 1 - pinned, updated_at=? WHERE id=?", (_now(), note_id))


def toggle_fav(note_id: int):
    with connect() as conn:
        conn.execute("UPDATE notes SET favorite = 1 - favorite, updated_at=? WHERE id=?", (_now(), note_id))


# ============================================================
# Toast 通知
# ============================================================
class Toast(ctk.CTkToplevel):
    def __init__(self, master, message: str, msg_type: str = "info", duration: int = 2000):
        super().__init__(master)
        self.overrideredirect(True)
        self.attributes("-topmost", True)

        colors = {
            "info": (COLOR_INFO, "#FFFFFF"),
            "success": (COLOR_SUCCESS, "#FFFFFF"),
            "warning": (COLOR_WARN, "#FFFFFF"),
            "error": (COLOR_DANGER, "#FFFFFF"),
        }
        bg, fg = colors.get(msg_type, colors["info"])

        frame = ctk.CTkFrame(self, fg_color=bg, corner_radius=12)
        frame.pack(fill="both", expand=True, padx=2, pady=2)
        ctk.CTkLabel(frame, text=f"  {message}  ", font=FONT_NORMAL, text_color=fg).pack(padx=16, pady=10)

        self.update_idletasks()
        w = self.winfo_reqwidth()
        x = master.winfo_rootx() + (master.winfo_width() - w) // 2
        y = master.winfo_rooty() + 60
        self.geometry(f"+{x}+{y}")
        self.after(duration, self.destroy)


# ============================================================
# 左侧导航栏
# ============================================================
NAV_ITEMS = [
    ("全部", "📋"),
    ("收藏", "⭐"),
    ("置顶", "📌"),
    ("最近更新", "🕐"),
    ("文件夹", "📁"),
]

FILE_TYPE_ITEMS = [
    ("文档", "📄", [".txt", ".md", ".doc", ".docx", ".pdf", ".rtf"]),
    ("图片", "🖼", [".jpg", ".jpeg", ".png", ".gif", ".svg", ".bmp", ".webp", ".ico"]),
    ("代码", "💻", [".py", ".js", ".ts", ".html", ".css", ".java", ".c", ".cpp", ".go", ".rs", ".rb", ".php"]),
    ("数据", "📊", [".json", ".xml", ".csv", ".xls", ".xlsx", ".yaml", ".yml", ".toml"]),
    ("压缩包", "📦", [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"]),
    ("视频", "🎬", [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv"]),
    ("音频", "🎵", [".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma"]),
]

# 排序选项
SORT_OPTIONS = [
    ("备注更新时间", "updated_at", True),
    ("备注创建时间", "created_at", True),
    ("文件修改时间", "file_modified", True),
    ("文件创建时间", "file_created", True),
    ("文件名 A-Z", "path", False),
    ("文件名 Z-A", "path", True),
]


class Sidebar(ctk.CTkFrame):
    def __init__(self, master, on_nav_change):
        super().__init__(master, width=260, corner_radius=0, fg_color=COLOR_BG_SIDEBAR)
        self.on_nav_change = on_nav_change
        self._current = ""
        self._nav_buttons: dict[str, ctk.CTkButton] = {}
        self._build()

    def _build(self):
        # Logo
        logo_frame = ctk.CTkFrame(self, fg_color="transparent")
        logo_frame.pack(fill="x", padx=20, pady=(28, 20))
        ctk.CTkLabel(logo_frame, text="📂", font=("Segoe UI Emoji", 36)).pack(side="left", padx=(0, 12))
        ctk.CTkLabel(logo_frame, text="FileNote", font=("微软雅黑", 24, "bold"), text_color=COLOR_PRIMARY).pack(side="left")

        ctk.CTkFrame(self, height=2, fg_color=COLOR_BORDER).pack(fill="x", padx=20, pady=(0, 16))

        # 导航
        ctk.CTkLabel(self, text="导航", font=FONT_SMALL, text_color=COLOR_TEXT_MUTED, anchor="w").pack(fill="x", padx=24, pady=(4, 8))

        for name, icon in NAV_ITEMS:
            btn = ctk.CTkButton(
                self, text=f"  {icon}  {name}", anchor="w", font=("微软雅黑", 14), height=44,
                fg_color="transparent", text_color=COLOR_TEXT_PRIMARY,
                hover_color=("gray85", "gray25"), corner_radius=10,
                command=lambda n=name: self._select_nav(n),
            )
            btn.pack(fill="x", padx=14, pady=2)
            self._nav_buttons[name] = btn

        # 文件类型
        ctk.CTkFrame(self, height=2, fg_color=COLOR_BORDER).pack(fill="x", padx=20, pady=(12, 8))
        ctk.CTkLabel(self, text="文件类型", font=FONT_SMALL, text_color=COLOR_TEXT_MUTED, anchor="w").pack(fill="x", padx=24, pady=(4, 8))

        for name, icon, exts in FILE_TYPE_ITEMS:
            btn = ctk.CTkButton(
                self, text=f"  {icon}  {name}", anchor="w", font=("微软雅黑", 12), height=34,
                fg_color="transparent", text_color=COLOR_TEXT_PRIMARY,
                hover_color=("gray85", "gray25"), corner_radius=8,
                command=lambda n=name, e=exts: self._select_file_type(n, e),
            )
            btn.pack(fill="x", padx=18, pady=1)
            self._nav_buttons[f"type:{name}"] = btn

        ctk.CTkFrame(self, height=2, fg_color=COLOR_BORDER).pack(fill="x", padx=20, pady=(12, 12))

        # 标签
        ctk.CTkLabel(self, text="标签", font=FONT_SMALL, text_color=COLOR_TEXT_MUTED, anchor="w").pack(fill="x", padx=24, pady=(4, 8))
        self._tag_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._tag_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        ctk.CTkLabel(self, text="v1.0-dev", font=FONT_SMALL, text_color=COLOR_TEXT_MUTED).pack(side="bottom", pady=12)
        self._select_nav("全部")

    def _select_nav(self, name: str):
        self._current = name
        for k, btn in self._nav_buttons.items():
            if k == name:
                btn.configure(fg_color=COLOR_PRIMARY, text_color="white")
            else:
                btn.configure(fg_color="transparent", text_color=COLOR_TEXT_PRIMARY)
        self.on_nav_change(name)

    def _select_file_type(self, name: str, exts: list[str]):
        self._current = f"type:{name}"
        for k, btn in self._nav_buttons.items():
            if k == f"type:{name}":
                btn.configure(fg_color=COLOR_PRIMARY, text_color="white")
            else:
                btn.configure(fg_color="transparent", text_color=COLOR_TEXT_PRIMARY)
        self.on_nav_change(f"type:{name}")

    def refresh_tags(self, tags: list[str]):
        for w in self._tag_frame.winfo_children():
            w.destroy()
        if not tags:
            ctk.CTkLabel(self._tag_frame, text="暂无标签", font=FONT_SMALL, text_color=COLOR_TEXT_MUTED).pack(pady=8)
            return
        for tag in tags:
            btn = ctk.CTkButton(
                self._tag_frame, text=f"  🏷️  {tag}", anchor="w", font=FONT_SMALL, height=32,
                fg_color="transparent", text_color=COLOR_TEXT_PRIMARY,
                hover_color=("gray85", "gray25"), corner_radius=6,
                command=lambda t=tag: self.on_nav_change(f"tag:{t}"),
            )
            btn.pack(fill="x", padx=4, pady=1)


# ============================================================
# 备注卡片
# ============================================================
class NoteCard(ctk.CTkFrame):
    def __init__(self, master, item: dict, on_select, on_context_menu, is_selected: bool = False):
        self._item = item
        self._on_select = on_select
        self._on_context_menu = on_context_menu
        self._is_selected = is_selected

        border_w = 2 if is_selected else 0
        super().__init__(master, corner_radius=10, fg_color=self._get_bg_color(), cursor="hand2",
                         border_width=border_w, border_color=COLOR_BORDER)
        self._build()
        self._bind_hover()

    def _get_bg_color(self):
        return COLOR_BG_SELECTED if self._is_selected else COLOR_BG_CARD

    def _build(self):
        item = self._item
        file_meta = get_file_times(item["path"])
        file_type = get_file_type(item["path"])
        icon = get_file_type_icon(item["path"])

        # 顶部行：图标 + 文件名
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=12, pady=(10, 2))

        # 图标（固定宽度，用 anchor="center" 居中）
        icon_label = ctk.CTkLabel(top, text=icon, font=FONT_ICON, width=28, anchor="center")
        icon_label.pack(side="left")

        # 文件名
        name = os.path.basename(item["path"]) or item["path"]
        name_label = ctk.CTkLabel(top, text=name, font=FONT_SUBTITLE, anchor="w",
                                   text_color=COLOR_TEXT_PRIMARY, wraplength=200)
        name_label.pack(side="left", padx=(8, 0), fill="x", expand=True)

        # 右侧状态
        right_frame = ctk.CTkFrame(top, fg_color="transparent")
        right_frame.pack(side="right")

        if item["pinned"]:
            ctk.CTkLabel(right_frame, text="📌", font=("Segoe UI Emoji", 12), width=20).pack(side="right", padx=1)
        if item["favorite"]:
            ctk.CTkLabel(right_frame, text="⭐", font=("Segoe UI Emoji", 12), width=20).pack(side="right", padx=1)

        # 文件类型标签（放在名字下方）
        type_frame = ctk.CTkFrame(self, fg_color="transparent")
        type_frame.pack(fill="x", padx=12, pady=(0, 4))

        type_badge = ctk.CTkLabel(type_frame, text=file_type, font=("Microsoft YaHei UI", 10),
                                   text_color="white", fg_color=COLOR_PRIMARY,
                                   corner_radius=4, width=60, height=20)
        type_badge.pack(side="left", padx=(36, 0))

        # 路径
        path_label = ctk.CTkLabel(self, text=item["path"], font=FONT_SMALL, text_color=COLOR_INFO,
                                   anchor="w", wraplength=300, cursor="hand2")
        path_label.pack(fill="x", padx=12, pady=(0, 4))
        path_label.bind("<Button-1>", lambda e: self._open_path(item["path"]))

        # 预览
        preview = item["note"][:100].replace("\n", " ")
        if len(item["note"]) > 100:
            preview += "..."
        if preview:
            ctk.CTkLabel(self, text=preview, font=FONT_SMALL, text_color=COLOR_TEXT_SECONDARY,
                          anchor="w", wraplength=300, justify="left").pack(fill="x", padx=12, pady=(0, 4))

        # 时间
        time_text = f"📁 {file_meta['file_modified']}  📝 {item['updated_at'][:16]}"
        ctk.CTkLabel(self, text=time_text, font=("Microsoft YaHei UI", 10),
                      text_color=COLOR_TEXT_MUTED, anchor="e").pack(fill="x", padx=12, pady=(0, 8))

    def _open_path(self, path: str):
        if os.path.exists(path):
            if os.path.isdir(path):
                os.startfile(path)
            else:
                os.startfile(os.path.dirname(path))
        else:
            Toast(self.winfo_toplevel(), "路径不存在", "warning")

    def _bind_hover(self):
        def on_enter(e):
            if not self._is_selected:
                self.configure(fg_color=COLOR_BG_CARD_HOVER)
        def on_leave(e):
            if not self._is_selected:
                self.configure(fg_color=COLOR_BG_CARD)

        self.bind("<Enter>", on_enter)
        self.bind("<Leave>", on_leave)
        self.bind("<Button-1>", lambda e: self._on_select(self._item))
        self.bind("<Button-3>", lambda e: self._on_context_menu(e, self._item))

        for child in self.winfo_children():
            child.bind("<Enter>", on_enter)
            child.bind("<Leave>", on_leave)
            child.bind("<Button-1>", lambda e: self._on_select(self._item))
            child.bind("<Button-3>", lambda e: self._on_context_menu(e, self._item))
            for grandchild in child.winfo_children():
                grandchild.bind("<Enter>", on_enter)
                grandchild.bind("<Leave>", on_leave)
                grandchild.bind("<Button-1>", lambda e: self._on_select(self._item))
                grandchild.bind("<Button-3>", lambda e: self._on_context_menu(e, self._item))


# ============================================================
# 备注列表
# ============================================================
class NoteList(ctk.CTkFrame):
    def __init__(self, master, on_select, on_search, on_sort_change):
        super().__init__(master, width=380, fg_color=COLOR_BG_MAIN)
        self.on_select = on_select
        self.on_search = on_search
        self.on_sort_change = on_sort_change
        self._items: list[dict] = []
        self._selected_id: int | None = None
        self._search_after_id: str | None = None
        self._sort_by = "updated_at"
        self._sort_desc = True
        self._build()

    def _build(self):
        # 搜索
        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.pack(fill="x", padx=12, pady=(12, 8))

        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", self._on_search_change)
        search_entry = ctk.CTkEntry(
            search_frame, placeholder_text="🔍 搜索路径或备注...",
            textvariable=self._search_var, font=FONT_NORMAL, height=38, corner_radius=10
        )
        search_entry.pack(fill="x")

        # 排序选择
        sort_frame = ctk.CTkFrame(self, fg_color="transparent")
        sort_frame.pack(fill="x", padx=12, pady=(0, 8))

        ctk.CTkLabel(sort_frame, text="排序:", font=FONT_SMALL, text_color=COLOR_TEXT_MUTED).pack(side="left")

        self._sort_var = ctk.StringVar(value="备注更新时间")
        sort_menu = ctk.CTkOptionMenu(
            sort_frame, variable=self._sort_var, values=[s[0] for s in SORT_OPTIONS],
            font=FONT_SMALL, width=130, height=28, corner_radius=6,
            fg_color=COLOR_PRIMARY, button_color=COLOR_PRIMARY_HOVER,
            command=self._on_sort_select
        )
        sort_menu.pack(side="left", padx=(4, 0))

        # 新增按钮
        add_btn = ctk.CTkButton(
            self, text="➕  新增备注", font=FONT_NORMAL, height=36,
            fg_color=COLOR_PRIMARY, hover_color=COLOR_PRIMARY_HOVER,
            corner_radius=10, command=self._add_note_dialog
        )
        add_btn.pack(fill="x", padx=12, pady=(0, 8))

        # 列表
        self._list_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._list_frame.pack(fill="both", expand=True, padx=4, pady=0)

        # 统计
        self._count_label = ctk.CTkLabel(self, text="", font=FONT_SMALL, text_color=COLOR_TEXT_MUTED)
        self._count_label.pack(fill="x", padx=12, pady=(4, 8))

    def _on_sort_select(self, choice: str):
        for name, sort_by, desc in SORT_OPTIONS:
            if name == choice:
                self._sort_by = sort_by
                self._sort_desc = desc
                self.on_sort_change(sort_by, desc)
                break

    def _on_search_change(self, *args):
        if self._search_after_id:
            self.after_cancel(self._search_after_id)
        self._search_after_id = self.after(300, lambda: self.on_search(self._search_var.get().strip()))

    def _add_note_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("新增文件备注")
        dialog.geometry("580x420")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="文件/文件夹路径：", font=FONT_NORMAL).pack(anchor="w", padx=20, pady=(18, 4))
        path_var = ctk.StringVar()
        ctk.CTkEntry(dialog, textvariable=path_var, font=FONT_NORMAL,
                      placeholder_text="输入或粘贴路径...", height=38, corner_radius=10).pack(fill="x", padx=20, pady=(0, 10))

        ctk.CTkLabel(dialog, text="备注内容（支持 Markdown）：", font=FONT_NORMAL).pack(anchor="w", padx=20, pady=(0, 4))
        note_text = ctk.CTkTextbox(dialog, font=FONT_MONO, wrap="word", corner_radius=10)
        note_text.pack(fill="both", expand=True, padx=20, pady=(0, 14))

        def save():
            path = path_var.get().strip()
            note = note_text.get("1.0", "end").strip()
            if not path:
                Toast(dialog, "请输入文件路径", "warning")
                return
            try:
                upsert_note(path, note)
                dialog.destroy()
                self.on_search(self._search_var.get().strip())
                Toast(self.winfo_toplevel(), "备注已保存", "success")
            except Exception:
                logger.exception("保存备注失败")
                Toast(dialog, "保存失败", "error")

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0, 18))
        ctk.CTkButton(btn_frame, text="保存", font=FONT_NORMAL, fg_color=COLOR_SUCCESS,
                       hover_color=COLOR_SUCCESS_HOVER, width=100, corner_radius=10, command=save).pack(side="right", padx=4)
        ctk.CTkButton(btn_frame, text="取消", font=FONT_NORMAL, fg_color="gray",
                       width=80, corner_radius=10, command=dialog.destroy).pack(side="right", padx=4)

    def load_items(self, items: list[dict]):
        self._items = items
        for w in self._list_frame.winfo_children():
            w.destroy()

        if not items:
            empty = ctk.CTkFrame(self._list_frame, fg_color="transparent")
            empty.pack(fill="both", expand=True, pady=60)
            ctk.CTkLabel(empty, text="📭", font=("Segoe UI Emoji", 56)).pack(pady=(0, 14))
            ctk.CTkLabel(empty, text="暂无备注", font=FONT_SUBTITLE, text_color=COLOR_TEXT_SECONDARY).pack()
            ctk.CTkLabel(empty, text="点击上方按钮添加", font=FONT_SMALL, text_color=COLOR_TEXT_MUTED).pack(pady=(4, 0))
            self._count_label.configure(text="共 0 条备注")
            return

        for item in items:
            is_selected = (item["id"] == self._selected_id)
            card = NoteCard(self._list_frame, item, on_select=self._on_card_select,
                           on_context_menu=self._show_context_menu, is_selected=is_selected)
            card.pack(fill="x", padx=8, pady=4)

        self._count_label.configure(text=f"共 {len(items)} 条备注")

    def _on_card_select(self, item: dict):
        self._selected_id = item["id"]
        self.on_select(item)
        self.load_items(self._items)

    def _show_context_menu(self, event, item: dict):
        menu = Menu(self, tearoff=0, font=FONT_SMALL)
        pin_text = "取消置顶" if item["pinned"] else "📌 置顶"
        fav_text = "取消收藏" if item["favorite"] else "⭐ 收藏"
        menu.add_command(label=pin_text, command=lambda: self._ctx_toggle_pin(item))
        menu.add_command(label=fav_text, command=lambda: self._ctx_toggle_fav(item))
        menu.add_separator()
        menu.add_command(label="📋 复制路径", command=lambda: self._ctx_copy_path(item))
        menu.add_command(label="📂 打开所在文件夹", command=lambda: self._ctx_open_folder(item))
        menu.add_separator()
        menu.add_command(label="🗑️ 删除", command=lambda: self._ctx_delete(item))
        menu.post(event.x_root, event.y_root)

    def _ctx_toggle_pin(self, item: dict):
        toggle_pin(item["id"])
        self.on_search(self._search_var.get().strip())

    def _ctx_toggle_fav(self, item: dict):
        toggle_fav(item["id"])
        self.on_search(self._search_var.get().strip())

    def _ctx_copy_path(self, item: dict):
        self.clipboard_clear()
        self.clipboard_append(item["path"])
        Toast(self.winfo_toplevel(), "路径已复制", "success")

    def _ctx_open_folder(self, item: dict):
        folder = item["path"] if os.path.isdir(item["path"]) else os.path.dirname(item["path"])
        if os.path.exists(folder):
            os.startfile(folder)
        else:
            Toast(self.winfo_toplevel(), "路径不存在", "warning")

    def _ctx_delete(self, item: dict):
        if messagebox.askyesno("确认删除", f"确定删除「{os.path.basename(item['path'])}」的备注？"):
            delete_note_by_id(item["id"])
            if self._selected_id == item["id"]:
                self._selected_id = None
            self.on_search(self._search_var.get().strip())
            Toast(self.winfo_toplevel(), "已删除", "info")


# ============================================================
# 详情面板
# ============================================================
class DetailPanel(ctk.CTkFrame):
    def __init__(self, master, on_refresh_list):
        super().__init__(master, fg_color=COLOR_BG_MAIN)
        self._current_item: dict | None = None
        self._on_refresh_list = on_refresh_list
        self._preview_visible = False
        self._build()

    def _build(self):
        self._empty_frame = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkLabel(self._empty_frame, text="📝", font=("Segoe UI Emoji", 80)).pack(pady=(120, 24))
        ctk.CTkLabel(self._empty_frame, text="选择一条备注查看详情", font=FONT_SUBTITLE, text_color=COLOR_TEXT_SECONDARY).pack()
        ctk.CTkLabel(self._empty_frame, text="或点击左侧「新增备注」创建", font=FONT_SMALL, text_color=COLOR_TEXT_MUTED).pack(pady=(6, 0))
        self._empty_frame.pack(expand=True, fill="both")

        self._detail_frame = ctk.CTkFrame(self, fg_color="transparent")

        # 操作栏
        action_bar = ctk.CTkFrame(self._detail_frame, fg_color="transparent")
        action_bar.pack(fill="x", padx=18, pady=(14, 10))

        self._save_btn = ctk.CTkButton(action_bar, text="💾 保存", width=80, font=FONT_SMALL,
                                        fg_color=COLOR_SUCCESS, hover_color=COLOR_SUCCESS_HOVER, corner_radius=10, height=36, command=self._save_note)
        self._save_btn.pack(side="right", padx=4)
        self._del_btn = ctk.CTkButton(action_bar, text="🗑️ 删除", width=80, font=FONT_SMALL,
                                       fg_color=COLOR_DANGER, hover_color=COLOR_DANGER_HOVER, corner_radius=10, height=36, command=self._delete_note)
        self._del_btn.pack(side="right", padx=4)
        self._preview_btn = ctk.CTkButton(action_bar, text="👁️ 预览", width=80, font=FONT_SMALL,
                                           fg_color=COLOR_INFO, hover_color="#2563EB", corner_radius=10, height=36, command=self._toggle_preview)
        self._preview_btn.pack(side="right", padx=4)
        self._fav_btn = ctk.CTkButton(action_bar, text="⭐ 收藏", width=80, font=FONT_SMALL,
                                       fg_color=COLOR_WARN, hover_color=COLOR_WARN_HOVER, corner_radius=10, height=36, command=self._toggle_fav)
        self._fav_btn.pack(side="left", padx=4)
        self._pin_btn = ctk.CTkButton(action_bar, text="📌 置顶", width=80, font=FONT_SMALL,
                                       fg_color=COLOR_PRIMARY, hover_color=COLOR_PRIMARY_HOVER, corner_radius=10, height=36, command=self._toggle_pin)
        self._pin_btn.pack(side="left", padx=4)

        ctk.CTkFrame(self._detail_frame, height=2, fg_color=COLOR_BORDER).pack(fill="x", padx=18, pady=6)

        # 路径
        path_frame = ctk.CTkFrame(self._detail_frame, fg_color="transparent")
        path_frame.pack(fill="x", padx=18, pady=(4, 2))
        ctk.CTkLabel(path_frame, text="📍 路径：", font=FONT_NORMAL, text_color=COLOR_TEXT_SECONDARY).pack(side="left")
        self._path_label = ctk.CTkLabel(path_frame, text="", font=FONT_NORMAL, text_color=COLOR_INFO, anchor="w", cursor="hand2")
        self._path_label.pack(side="left", fill="x", expand=True)
        self._path_label.bind("<Button-1>", lambda e: self._open_current_path())

        # 时间
        self._time_label = ctk.CTkLabel(self._detail_frame, text="", font=FONT_SMALL, text_color=COLOR_TEXT_MUTED, anchor="w")
        self._time_label.pack(fill="x", padx=22, pady=(0, 10))

        ctk.CTkFrame(self._detail_frame, height=2, fg_color=COLOR_BORDER).pack(fill="x", padx=18, pady=(0, 10))

        # 编辑器/预览
        self._editor_frame = ctk.CTkFrame(self._detail_frame, fg_color="transparent")
        self._preview_frame = ctk.CTkFrame(self._detail_frame, fg_color="transparent")

        ctk.CTkLabel(self._editor_frame, text="备注内容（Markdown）", font=FONT_SMALL, text_color=COLOR_TEXT_SECONDARY, anchor="w").pack(fill="x", padx=2, pady=(0, 6))
        self._editor = ctk.CTkTextbox(self._editor_frame, font=FONT_MONO, wrap="word", corner_radius=10, border_width=1)
        self._editor.pack(fill="both", expand=True)

        try:
            from tkinterweb import HtmlFrame
            self._html_frame = HtmlFrame(self._preview_frame, messages_enabled=False)
            self._html_frame.pack(fill="both", expand=True)
        except ImportError:
            self._html_frame = None
            ctk.CTkLabel(self._preview_frame, text="需要安装 tkinterweb", font=FONT_NORMAL, text_color=COLOR_TEXT_MUTED).pack(expand=True)

    def _open_current_path(self):
        if self._current_item:
            path = self._current_item["path"]
            if os.path.exists(path):
                os.startfile(path if os.path.isdir(path) else os.path.dirname(path))
            else:
                Toast(self.winfo_toplevel(), "路径不存在", "warning")

    def _toggle_preview(self):
        if not self._current_item:
            return
        self._preview_visible = not self._preview_visible

        if self._preview_visible:
            self._editor_frame.pack_forget()
            self._preview_frame.pack(fill="both", expand=True, padx=18, pady=(0, 18))
            self._preview_btn.configure(text="✏️ 编辑")
            self._render_markdown()
        else:
            self._preview_frame.pack_forget()
            self._editor_frame.pack(fill="both", expand=True, padx=18, pady=(0, 18))
            self._preview_btn.configure(text="👁️ 预览")

    def _render_markdown(self):
        if not self._html_frame or not self._current_item:
            return

        md_text = self._editor.get("1.0", "end").strip()
        html_content = markdown.markdown(md_text, extensions=['fenced_code', 'tables', 'nl2br']) if md_text else "<p style='color:gray;'>暂无内容</p>"

        full_html = f"""<!DOCTYPE html><html><head><style>
        body {{ font-family: 'Microsoft YaHei UI', sans-serif; font-size: 14px; line-height: 1.8; color: #1f2937; padding: 16px; }}
        h1 {{ font-size: 1.8em; border-bottom: 2px solid #e5e7eb; padding-bottom: 0.3em; }}
        h2 {{ font-size: 1.5em; border-bottom: 1px solid #e5e7eb; }}
        h3 {{ font-size: 1.3em; }}
        code {{ background: #f3f4f6; padding: 2px 6px; border-radius: 4px; font-family: 'Ubuntu Mono', monospace; }}
        pre {{ background: #1f2937; color: #f9fafb; padding: 16px; border-radius: 8px; overflow-x: auto; }}
        pre code {{ background: transparent; color: inherit; padding: 0; }}
        blockquote {{ border-left: 4px solid #6366f1; padding-left: 16px; color: #6b7280; }}
        a {{ color: #3b82f6; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #e5e7eb; padding: 8px 12px; }}
        th {{ background: #f9fafb; }}
        </style></head><body>{html_content}</body></html>"""
        self._html_frame.load_html(full_html)

    def show_empty(self):
        self._detail_frame.pack_forget()
        self._empty_frame.pack(expand=True, fill="both")
        self._current_item = None

    def show_detail(self, item: dict):
        self._empty_frame.pack_forget()
        self._detail_frame.pack(fill="both", expand=True)
        self._current_item = item

        self._path_label.configure(text=item["path"])
        file_meta = get_file_times(item["path"])
        self._time_label.configure(
            text=f"📁 文件创建: {file_meta['file_created']}  |  文件修改: {file_meta['file_modified']}  |  📝 备注更新: {item['updated_at'][:16]}"
        )
        self._editor.delete("1.0", "end")
        self._editor.insert("1.0", item["note"])

        self._pin_btn.configure(text="取消置顶" if item["pinned"] else "📌 置顶")
        self._fav_btn.configure(text="取消收藏" if item["favorite"] else "⭐ 收藏")

        self._preview_frame.pack_forget()
        self._editor_frame.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        self._preview_btn.configure(text="👁️ 预览")
        self._preview_visible = False

    def _toggle_pin(self):
        if self._current_item:
            toggle_pin(self._current_item["id"])
            self._on_refresh_list()

    def _toggle_fav(self):
        if self._current_item:
            toggle_fav(self._current_item["id"])
            self._on_refresh_list()

    def _delete_note(self):
        if not self._current_item:
            return
        name = os.path.basename(self._current_item['path']) or self._current_item['path']
        if messagebox.askyesno("确认删除", f"确定删除「{name}」的备注？"):
            delete_note_by_id(self._current_item["id"])
            self.show_empty()
            self._on_refresh_list()

    def _save_note(self):
        if not self._current_item:
            return
        new_note = self._editor.get("1.0", "end").strip()
        try:
            upsert_note(self._current_item["path"], new_note,
                        pinned=self._current_item["pinned"],
                        favorite=self._current_item["favorite"])
            Toast(self.winfo_toplevel(), "保存成功", "success")
            self._on_refresh_list()
        except Exception:
            logger.exception("保存备注失败")
            Toast(self.winfo_toplevel(), "保存失败", "error")


# ============================================================
# 主窗口
# ============================================================
class ManagerWindow(ctk.CTk):
    def __init__(self, target_path: str | None = None):
        super().__init__()
        self.title("📂 FileNote - 文件备注管理器")
        self.geometry("1360x820")
        self.minsize(1100, 700)

        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self._target_path = target_path
        self._nav_state = "全部"
        self._keyword = ""
        self._sort_by = "updated_at"
        self._sort_desc = True
        self._ready = False

        self._build_layout()
        self._bind_shortcuts()

        self._ready = True
        self.after(100, self._load_data)

    def _build_layout(self):
        self._sidebar = Sidebar(self, on_nav_change=self._on_nav_change)
        self._sidebar.pack(side="left", fill="y")

        self._note_list = NoteList(self, on_select=self._on_select, on_search=self._on_search, on_sort_change=self._on_sort_change)
        self._note_list.pack(side="left", fill="both", padx=(2, 0))

        self._detail = DetailPanel(self, on_refresh_list=self._load_data)
        self._detail.pack(side="right", fill="both", expand=True, padx=(0, 2))
        self._detail.show_empty()

    def _bind_shortcuts(self):
        self.bind("<Control-n>", lambda e: self._note_list._add_note_dialog())
        self.bind("<Control-f>", lambda e: self.focus_search())
        self.bind("<Delete>", lambda e: self._delete_selected())
        self.bind("<F5>", lambda e: self._load_data())

    def focus_search(self):
        for child in self._note_list.winfo_children():
            if isinstance(child, ctk.CTkFrame):
                for grandchild in child.winfo_children():
                    if isinstance(grandchild, ctk.CTkEntry):
                        grandchild.focus_set()
                        return

    def _delete_selected(self):
        if self._detail._current_item:
            self._detail._delete_note()

    def _on_nav_change(self, nav: str):
        self._nav_state = nav
        if self._ready:
            self._load_data()

    def _on_search(self, keyword: str):
        self._keyword = keyword
        self._load_data()

    def _on_sort_change(self, sort_by: str, sort_desc: bool):
        self._sort_by = sort_by
        self._sort_desc = sort_desc
        self._load_data()

    def _on_select(self, item: dict):
        self._detail.show_detail(item)

    def _load_data(self):
        nav = self._nav_state
        kw = self._keyword

        kwargs = {
            "keyword": kw,
            "sort_by": self._sort_by,
            "sort_desc": self._sort_desc,
        }

        if nav == "全部":
            items = fetch_notes(**kwargs)
        elif nav == "收藏":
            items = fetch_notes(only_fav=True, **kwargs)
        elif nav == "置顶":
            items = fetch_notes(only_pinned=True, **kwargs)
        elif nav == "文件夹":
            items = fetch_notes(only_folder=True, **kwargs)
        elif nav == "最近更新":
            items = fetch_notes(**kwargs)
        elif nav.startswith("tag:"):
            items = fetch_notes(tag=nav[4:], **kwargs)
        elif nav.startswith("type:"):
            type_name = nav[5:]
            for name, icon, exts in FILE_TYPE_ITEMS:
                if name == type_name:
                    items = fetch_notes(file_type_exts=exts, **kwargs)
                    break
            else:
                items = fetch_notes(**kwargs)
        else:
            items = fetch_notes(**kwargs)

        self._note_list.load_items(items)
        tags = fetch_tags()
        self._sidebar.refresh_tags(tags)
