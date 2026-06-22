@echo off
chcp 65001 >nul
echo ========================================
echo    FileNote 打包脚本
echo ========================================
echo.

set PYTHON=D:\Environment\Python\python3.12\python.exe

echo [1/3] 清理旧文件...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist __pycache__ rmdir /s /q __pycache__
echo [完成] 清理完成

echo.
echo [2/3] 开始打包...
"%PYTHON%" -m PyInstaller filenote.spec --clean --noconfirm
if %errorlevel% neq 0 (
    echo [错误] 打包失败
    pause
    exit /b 1
)
echo [完成] 打包成功

echo.
echo [3/3] 检查结果...
if exist "dist\FileNote\FileNote.exe" (
    echo [成功] FileNote.exe 已生成
    echo 位置：%~dp0dist\FileNote\FileNote.exe
    echo.
    echo 运行 install.bat 进行安装
) else (
    echo [错误] 找不到生成的 exe
)

echo.
pause
