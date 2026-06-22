"""
FileNote 主窗口管理器
- 左侧：分类导航（全部、收藏、最近、标签）
- 中间：备注列表（搜索/筛选/排序）
- 右侧：详情（Markdown 编辑/预览）
"""

import os
import sqlite3
import datetime as dt
import customtkinter as ctk
from tkinter import messagebox
from loguru import logger
from data.store import connect, _now

# ============================================================
# 颜色/字体常量
# ============================================================
FONT_TITLE = ("Microsoft YaHei UI", 18, "bold")
FONT_NORMAL = ("Microsoft YaHei UI", 13)
FONT_SMALL = ("Microsoft YaHei UI", 11)
FONT_MONO = ("Consolas", 12)

COLOR_ACCENT = "#3B82F6"
COLOR_WARN = "#EF4444"
COLOR_SUCCESS = "#10B981"


# ============================================================
# 数据辅助
# ============================================================
def fetch_notes(keyword: str = "", tag: str | None = None,
                only_pinned: bool = False, only_fav: bool = False,
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
    sql += " ORDER BY pinned DESC, updated_at DESC LIMIT ?"
    params.append(limit)
    with connect() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


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
# 左侧导航栏
# ============================================================
class Sidebar(ctk.CTkFrame):
    def __init__(self, master, on_nav_change):
        super().__init__(master, width=200, corner_radius=0)
        self.on_nav_change = on_nav_change
        self._build()

    def _build(self):
        title = ctk.CTkLabel(self, text="FileNote", font=FONT_TITLE, anchor="w")
        title.pack(fill="x", padx=16, pady=(18, 10))

        ctk.CTkLabel(self, text="导航", font=FONT_SMALL, text_color="gray", anchor="w").pack(fill="x", padx=16, pady=(8, 2))

        nav_items = ["全部", "收藏", "置顶", "最近修改"]
        self._nav_buttons: dict[str, ctk.CTkButton] = {}
        for item in nav_items:
            btn = ctk.CTkButton(
                self, text=item, anchor="w", font=FONT_NORMAL, height=36,
                fg_color="transparent", text_color=("gray10", "gray90"),
                hover_color=("gray75", "gray30"),
                command=lambda n=item: self._select_nav(n),
            )
            btn.pack(fill="x", padx=8, pady=2)
            self._nav_buttons[item] = btn

        ctk.CTkLabel(self, text="标签", font=FONT_SMALL, text_color="gray", anchor="w").pack(fill="x", padx=16, pady=(14, 2))

        self._tag_frame = ctk.CTkScrollableFrame(self, height=200)
        self._tag_frame.pack(fill="both", expand=True, padx=8, pady=4)

        # 默认选中"全部"
        self._select_nav("全部")

    def _select_nav(self, name: str):
        for k, btn in self._nav_buttons.items():
            if k == name:
                btn.configure(fg_color=COLOR_ACCENT, text_color="white")
            else:
                btn.configure(fg_color="transparent", text_color=("gray10", "gray90"))
        self.on_nav_change(name)

    def refresh_tags(self, tags: list[str]):
        for w in self._tag_frame.winfo_children():
            w.destroy()
        for tag in tags:
            btn = ctk.CTkButton(
                self._tag_frame, text=tag, anchor="w", font=FONT_SMALL, height=28,
                fg_color="transparent", text_color=("gray10", "gray90"),
                hover_color=("gray75", "gray30"),
                command=lambda t=tag: self.on_nav_change(f"tag:{t}"),
            )
            btn.pack(fill="x", padx=4, pady=1)


# ============================================================
# 中间备注列表
# ============================================================
class NoteList(ctk.CTkFrame):
    def __init__(self, master, on_select, on_search):
        super().__init__(master, width=320)
        self.on_select = on_select
        self._items: list[dict] = []
        self._build()

    def _build(self):
        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.pack(fill="x", padx=8, pady=(8, 4))

        self._search_var = ctk.StringVar()
        search_entry = ctk.CTkEntry(search_frame, placeholder_text="搜索文件路径或备注...",
                                     textvariable=self._search_var, font=FONT_NORMAL)
        search_entry.pack(fill="x", side="left", expand=True, padx=(0, 4))
        search_entry.bind("<Return>", lambda e: self._do_search())

        search_btn = ctk.CTkButton(search_frame, text="搜索", width=60, font=FONT_SMALL,
                                    command=self._do_search)
        search_btn.pack(side="right")

        add_btn = ctk.CTkButton(self, text="新增备注", font=FONT_NORMAL, height=34,
                                 fg_color=COLOR_SUCCESS, hover_color="#059669",
                                 command=self._add_note_dialog)
        add_btn.pack(fill="x", padx=8, pady=4)

        self._list_frame = ctk.CTkScrollableFrame(self)
        self._list_frame.pack(fill="both", expand=True, padx=4, pady=4)

        self._count_label = ctk.CTkLabel(self, text="共 0 条", font=FONT_SMALL, text_color="gray")
        self._count_label.pack(fill="x", padx=8, pady=(0, 6))

    def _do_search(self):
        self.on_search(self._search_var.get().strip())

    def _add_note_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("新增文件备注")
        dialog.geometry("520x340")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="文件/文件夹路径：", font=FONT_NORMAL).pack(anchor="w", padx=16, pady=(14, 2))
        path_var = ctk.StringVar()
        path_entry = ctk.CTkEntry(dialog, textvariable=path_var, font=FONT_NORMAL,
                                   placeholder_text="输入文件路径...")
        path_entry.pack(fill="x", padx=16, pady=4)

        ctk.CTkLabel(dialog, text="备注内容（Markdown）：", font=FONT_NORMAL).pack(anchor="w", padx=16, pady=(8, 2))
        note_text = ctk.CTkTextbox(dialog, font=FONT_MONO, wrap="word")
        note_text.pack(fill="both", expand=True, padx=16, pady=4)

        def save():
            path = path_var.get().strip()
            note = note_text.get("1.0", "end").strip()
            if not path:
                messagebox.showwarning("提示", "请输入路径", parent=dialog)
                return
            try:
                upsert_note(path, note)
                dialog.destroy()
                self.on_search(self._search_var.get().strip())
            except Exception:
                logger.exception("保存备注失败")
                messagebox.showerror("错误", "保存失败", parent=dialog)

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=8)
        ctk.CTkButton(btn_frame, text="保存", font=FONT_NORMAL, fg_color=COLOR_SUCCESS,
                       hover_color="#059669", command=save).pack(side="right", padx=4)
        ctk.CTkButton(btn_frame, text="取消", font=FONT_NORMAL, fg_color="gray",
                       command=dialog.destroy).pack(side="right", padx=4)

    def load_items(self, items: list[dict]):
        self._items = items
        for w in self._list_frame.winfo_children():
            w.destroy()
        if not items:
            ctk.CTkLabel(self._list_frame, text="暂无备注，点击上方添加",
                         font=FONT_NORMAL, text_color="gray").pack(pady=40)
            self._count_label.configure(text="共 0 条")
            return
        for item in items:
            self._create_item_card(item)
        self._count_label.configure(text=f"共 {len(items)} 条")

    def _create_item_card(self, item: dict):
        frame = ctk.CTkFrame(self._list_frame, corner_radius=8)
        frame.pack(fill="x", padx=4, pady=3)

        icons = ("[置顶] " if item["pinned"] else "") + ("[收藏] " if item["favorite"] else "")
        name = os.path.basename(item["path"]) or item["path"]

        title_label = ctk.CTkLabel(frame, text=f"{icons}{name}", font=FONT_NORMAL,
                                    anchor="w", wraplength=280)
        title_label.pack(fill="x", padx=10, pady=(6, 0))

        path_label = ctk.CTkLabel(frame, text=item["path"], font=FONT_SMALL,
                                   text_color="gray", anchor="w", wraplength=280)
        path_label.pack(fill="x", padx=10)

        preview = item["note"][:80] + "..." if len(item["note"]) > 80 else item["note"]
        if preview:
            preview_label = ctk.CTkLabel(frame, text=preview, font=FONT_SMALL,
                                          text_color=("gray40", "gray60"), anchor="w",
                                          wraplength=280, justify="left")
            preview_label.pack(fill="x", padx=10, pady=(0, 4))

        time_label = ctk.CTkLabel(frame, text=f"更新: {item['updated_at']}", font=FONT_SMALL,
                                   text_color="gray", anchor="e")
        time_label.pack(fill="x", padx=10, pady=(0, 6))

        for widget in (frame, title_label, path_label):
            widget.bind("<Button-1>", lambda e, n=item: self.on_select(n))


# ============================================================
# 右侧详情面板
# ============================================================
class DetailPanel(ctk.CTkFrame):
    def __init__(self, master, on_refresh_list):
        super().__init__(master)
        self._current_item: dict | None = None
        self._on_refresh_list = on_refresh_list
        self._build()

    def _build(self):
        self._empty_label = ctk.CTkLabel(self, text="选择一条备注查看详情",
                                          font=FONT_TITLE, text_color="gray")
        self._empty_label.pack(expand=True)

        self._detail_frame = ctk.CTkFrame(self, fg_color="transparent")

        action_bar = ctk.CTkFrame(self._detail_frame, fg_color="transparent")
        action_bar.pack(fill="x", padx=8, pady=(8, 4))

        self._pin_btn = ctk.CTkButton(action_bar, text="置顶", width=70, font=FONT_SMALL,
                                       command=self._toggle_pin)
        self._pin_btn.pack(side="left", padx=2)
        self._fav_btn = ctk.CTkButton(action_bar, text="收藏", width=70, font=FONT_SMALL,
                                       command=self._toggle_fav)
        self._fav_btn.pack(side="left", padx=2)
        self._del_btn = ctk.CTkButton(action_bar, text="删除", width=70, font=FONT_SMALL,
                                       fg_color=COLOR_WARN, hover_color="#DC2626",
                                       command=self._delete_note)
        self._del_btn.pack(side="left", padx=2)
        self._save_btn = ctk.CTkButton(action_bar, text="保存", width=70, font=FONT_SMALL,
                                        fg_color=COLOR_SUCCESS, hover_color="#059669",
                                        command=self._save_note)
        self._save_btn.pack(side="right", padx=2)

        path_frame = ctk.CTkFrame(self._detail_frame, fg_color="transparent")
        path_frame.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(path_frame, text="路径：", font=FONT_NORMAL).pack(side="left")
        self._path_label = ctk.CTkLabel(path_frame, text="", font=FONT_NORMAL,
                                         text_color=COLOR_ACCENT, anchor="w")
        self._path_label.pack(side="left", fill="x", expand=True)

        self._time_label = ctk.CTkLabel(self._detail_frame, text="", font=FONT_SMALL,
                                         text_color="gray", anchor="w")
        self._time_label.pack(fill="x", padx=12)

        self._editor = ctk.CTkTextbox(self._detail_frame, font=FONT_MONO, wrap="word")
        self._editor.pack(fill="both", expand=True, padx=8, pady=8)

    def show_empty(self):
        self._detail_frame.pack_forget()
        self._empty_label.pack(expand=True)
        self._current_item = None

    def show_detail(self, item: dict):
        self._empty_label.pack_forget()
        self._detail_frame.pack(fill="both", expand=True)
        self._current_item = item
        self._path_label.configure(text=item["path"])
        self._time_label.configure(
            text=f"创建: {item['created_at']}  |  更新: {item['updated_at']}"
        )
        self._editor.delete("1.0", "end")
        self._editor.insert("1.0", item["note"])
        self._pin_btn.configure(text="已置顶" if item["pinned"] else "置顶")
        self._fav_btn.configure(text="已收藏" if item["favorite"] else "收藏")

    def _toggle_pin(self):
        if not self._current_item:
            return
        toggle_pin(self._current_item["id"])
        self._on_refresh_list()

    def _toggle_fav(self):
        if not self._current_item:
            return
        toggle_fav(self._current_item["id"])
        self._on_refresh_list()

    def _delete_note(self):
        if not self._current_item:
            return
        if messagebox.askyesno("确认删除", f"确定删除「{self._current_item['path']}」的备注？"):
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
            self._on_refresh_list()
        except Exception:
            logger.exception("保存备注失败")
            messagebox.showerror("错误", "保存失败")


# ============================================================
# 主窗口
# ============================================================
class ManagerWindow(ctk.CTk):
    def __init__(self, target_path: str | None = None):
        super().__init__()
        self.title("FileNote - 文件备注管理器")
        self.geometry("1200x720")
        self.minsize(960, 600)

        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self._target_path = target_path
        self._nav_state = "全部"
        self._keyword = ""
        self._ready = False

        self._build_layout()
        self._ready = True
        self.after(100, self._load_data)

    def _build_layout(self):
        self._sidebar = Sidebar(self, on_nav_change=self._on_nav_change)
        self._sidebar.pack(side="left", fill="y")

        self._note_list = NoteList(self, on_select=self._on_select, on_search=self._on_search)
        self._note_list.pack(side="left", fill="both", padx=(2, 0))

        self._detail = DetailPanel(self, on_refresh_list=self._load_data)
        self._detail.pack(side="right", fill="both", expand=True, padx=(0, 2))
        self._detail.show_empty()

    def _on_nav_change(self, nav: str):
        self._nav_state = nav
        if self._ready:
            self._load_data()

    def _on_search(self, keyword: str):
        self._keyword = keyword
        self._load_data()

    def _on_select(self, item: dict):
        self._detail.show_detail(item)

    def _load_data(self):
        nav = self._nav_state
        kw = self._keyword

        if nav == "全部":
            items = fetch_notes(keyword=kw)
        elif nav == "收藏":
            items = fetch_notes(keyword=kw, only_fav=True)
        elif nav == "置顶":
            items = fetch_notes(keyword=kw, only_pinned=True)
        elif nav == "最近修改":
            items = fetch_notes(keyword=kw)
        elif nav.startswith("tag:"):
            items = fetch_notes(keyword=kw, tag=nav[4:])
        else:
            items = fetch_notes(keyword=kw)

        self._note_list.load_items(items)
        tags = fetch_tags()
        self._sidebar.refresh_tags(tags)
