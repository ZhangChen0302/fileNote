# FileNote - 文件备注管理工具

一个 Windows 平台的文件/文件夹备注管理工具，支持右键菜单快速编辑和独立管理器窗口。

## 功能特点

- **右键菜单集成**：在文件/文件夹上右键即可快速查看和编辑备注
- **独立管理器**：支持搜索、筛选、标签分类、置顶、收藏等功能
- **Markdown 支持**：备注内容支持 Markdown 格式
- **系统主题跟随**：自动跟随 Windows 深色/浅色主题
- **数据持久化**：使用 SQLite 存储，支持从旧版 JSON 自动迁移

## 安装要求

- Windows 10/11
- Python 3.10+

## 安装步骤

1. 克隆或下载此项目
2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
3. 运行 `install.bat` 或手动注册右键菜单：
   ```bash
   python main.py --register
   ```

## 打包构建

使用 PyInstaller 打包为独立可执行文件：

```bash
build.bat
```

打包产物位于 `dist/FileNote/`，运行 `install.bat` 可自动注册右键菜单并创建桌面快捷方式。

## 使用方法

### 右键菜单
- 右键任意文件 → "文件备注"
- 右键任意文件夹 → "文件夹备注"
- 弹出快速编辑窗口，编辑后保存即可

### 管理器窗口
```bash
python main.py              # 启动管理器
python main.py --gui        # 启动管理器
python main.py --gui "C:\path\to\file"  # 定位到指定文件
```

### 其他命令
```bash
python main.py --register    # 注册右键菜单（需管理员）
python main.py --unregister  # 注销右键菜单
python main.py --quick "path" # 快速编辑指定路径的备注
```

## 数据存储

- 数据库位置：`%LOCALAPPDATA%\FileNote\notes.db`
- 旧版 JSON 数据会自动迁移到 SQLite

## 项目结构

```
fileNote/
├── main.py                 # 主入口
├── main.legacy.py          # 旧版代码备份
├── ui/
│   └── manager.py          # 主窗口管理器 UI
├── data/
│   └── store.py            # 数据层（SQLite）
├── registry/
│   └── context_menu.py     # 右键菜单注册
├── utils/                  # 工具函数（预留）
├── build.bat               # PyInstaller 打包脚本
├── install.bat             # 安装脚本
├── filenote.spec            # PyInstaller 配置
├── requirements.txt        # 依赖列表
├── AGENTS.md               # 贡献者指南
└── README.md               # 说明文档
```

## 许可证

MIT License

## 贡献指南

欢迎提交 Issue 和 Pull Request。详细的开发规范请参阅 [AGENTS.md](AGENTS.md)。
