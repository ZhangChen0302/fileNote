import os
import json
import datetime
import winreg
import ctypes
from tkinter import Tk, simpledialog, messagebox

# 存储备注信息的文件路径
NOTES_FILE = os.path.join(os.path.expanduser('~'), '.file_notes.json')

class FileNoteApp:
    def __init__(self):
        # 加载现有的备注信息
        self.notes = self._load_notes()

    def _load_notes(self):
        """加载存储的备注信息"""
        if os.path.exists(NOTES_FILE):
            try:
                with open(NOTES_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_notes(self):
        """保存备注信息"""
        with open(NOTES_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.notes, f, ensure_ascii=False, indent=2)

    def add_note(self, path, note):
        """添加或更新文件/文件夹的备注"""
        # 规范化路径
        path = os.path.normpath(path)
        # 记录当前时间
        timestamp = datetime.datetime.now().isoformat()

        if path in self.notes:
            # 更新现有备注
            self.notes[path]['note'] = note
            self.notes[path]['updated_at'] = timestamp
        else:
            # 添加新备注
            self.notes[path] = {
                'note': note,
                'created_at': timestamp,
                'updated_at': timestamp
            }

        self._save_notes()
        return True

    def get_note(self, path):
        """获取文件/文件夹的备注"""
        path = os.path.normpath(path)
        return self.notes.get(path, None)

    def register_context_menu(self):
        """注册右键菜单"""
        try:
            # 创建主键
            key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, '*\shell\FileNote')
            winreg.SetValueEx(key, '', 0, winreg.REG_SZ, '文件备注')

            # 创建子键 command
            command_key = winreg.CreateKey(key, 'command')
            # 获取当前脚本路径
            script_path = os.path.abspath(__file__)
            # 设置命令，%1 表示选中的文件路径
            # winreg.SetValueEx(command_key, '', 0, winreg.REG_SZ, f'python "{script_path}" "%1"')
            python_path = sys.executable
            winreg.SetValueEx(command_key, '', 0, winreg.REG_SZ, f'"{python_path}" "{script_path}" "%1"')

            winreg.CloseKey(command_key)
            winreg.CloseKey(key)

            # 也为文件夹注册右键菜单
            dir_key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, 'Directory\shell\FileNote')
            winreg.SetValueEx(dir_key, '', 0, winreg.REG_SZ, '文件夹备注')

            dir_command_key = winreg.CreateKey(dir_key, 'command')
            # winreg.SetValueEx(dir_command_key, '', 0, winreg.REG_SZ, f'python "{script_path}" "%1"')
            winreg.SetValueEx(dir_command_key, '', 0, winreg.REG_SZ, f'"{python_path}" "{script_path}" "%1"')


            winreg.CloseKey(dir_command_key)
            winreg.CloseKey(dir_key)

            return True
        except Exception as e:
            print(f"注册右键菜单失败: {e}")
            return False

    def unregister_context_menu(self):
        """注销右键菜单"""
        try:
            winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, '*\shell\FileNote\command')
            winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, '*\shell\FileNote')

            winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, 'Directory\shell\FileNote\command')
            winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, 'Directory\shell\FileNote')

            return True
        except Exception as e:
            print(f"注销右键菜单失败: {e}")
            return False

    def show_note_dialog(self, path):
        """显示备注对话框"""
        root = Tk()
        root.withdraw()  # 隐藏主窗口

        note_data = self.get_note(path)
        if note_data:
            # 显示现有备注
            note_text = note_data['note']
            created_at = note_data['created_at']
            updated_at = note_data['updated_at']

            message = f"路径: {path}\n\n创建时间: {created_at}\n更新时间: {updated_at}\n\n备注:\n{note_text}"
            messagebox.showinfo("文件备注", message)

            # 询问是否编辑
            if messagebox.askyesno("编辑备注", "是否要编辑这个备注?"):
                new_note = simpledialog.askstring("编辑备注", "请输入新的备注:", initialvalue=note_text)
                if new_note is not None:
                    self.add_note(path, new_note)
                    messagebox.showinfo("成功", "备注已更新!")
        else:
            # 添加新备注
            new_note = simpledialog.askstring("添加备注", "请输入备注:")
            if new_note is not None:
                self.add_note(path, new_note)
                messagebox.showinfo("成功", "备注已添加!")

        root.destroy()

if __name__ == '__main__':
    import sys

    app = FileNoteApp()

    # 检查命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] == '--register':
            # 注册右键菜单
            if app.register_context_menu():
                print("右键菜单已成功注册!")
            else:
                print("注册右键菜单失败!")
        elif sys.argv[1] == '--unregister':
            # 注销右键菜单
            if app.unregister_context_menu():
                print("右键菜单已成功注销!")
            else:
                print("注销右键菜单失败!")
        else:
            # 显示备注对话框
            target_path = sys.argv[1]
            app.show_note_dialog(target_path)
    else:
        # 无参数，显示主界面
        root = Tk()
        root.title("文件备注工具")
        root.geometry("300x200")

        def register_menu():
            if app.register_context_menu():
                messagebox.showinfo("成功", "右键菜单已注册!")
            else:
                messagebox.showerror("失败", "注册右键菜单失败!")

        def unregister_menu():
            if app.unregister_context_menu():
                messagebox.showinfo("成功", "右键菜单已注销!")
            else:
                messagebox.showerror("失败", "注销右键菜单失败!")

        # 添加按钮
        btn_register = ctypes.windll.user32.MessageBoxW(0, "是否注册右键菜单?", "文件备注工具", 4)
        if btn_register == 6:
            register_menu()
        else:
            btn_unregister = ctypes.windll.user32.MessageBoxW(0, "是否注销右键菜单?", "文件备注工具", 4)
            if btn_unregister == 6:
                unregister_menu()

        root.mainloop()