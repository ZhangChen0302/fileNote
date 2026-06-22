@echo off
chcp 65001 >nul
echo ========================================
echo    FileNote - 文件备注管理工具 安装
echo ========================================
echo.

set EXE_PATH=%~dp0dist\FileNote\FileNote.exe

if not exist "%EXE_PATH%" (
    echo [错误] 找不到 FileNote.exe
    echo 请先运行打包脚本生成 exe
    pause
    exit /b 1
)

echo [1/2] 注册右键菜单...
"%EXE_PATH%" --register
if %errorlevel% equ 0 (
    echo [成功] 右键菜单已注册
) else (
    echo [失败] 右键菜单注册失败，请以管理员身份运行
)

echo.
echo [2/2] 创建桌面快捷方式...
set SHORTCUT=%USERPROFILE%\Desktop\FileNote.lnk
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT%'); $s.TargetPath = '%EXE_PATH%'; $s.WorkingDirectory = '%~dp0dist\FileNote'; $s.Description = '文件备注管理工具'; $s.Save()"
if exist "%SHORTCUT%" (
    echo [成功] 桌面快捷方式已创建
) else (
    echo [提示] 创建快捷方式失败
)

echo.
echo ========================================
echo    安装完成！
echo ========================================
echo.
echo 使用方法：
echo   1. 右键任意文件/文件夹 → 选择"文件备注"或"文件夹备注"
echo   2. 双击桌面快捷方式打开管理器
echo   3. 命令行：%EXE_PATH% --gui
echo.
pause
