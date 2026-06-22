@echo off

:: Simple batch file to register/unregister context menu for FileNote

cls

echo File Note Tool Setup
 echo ===============

:menu
cls
echo Please choose an option:
echo 1. Register context menu
echo 2. Unregister context menu
echo 3. Exit

getinput:
set "choice="
set /p choice=Enter option (1-3): 

if not defined choice (
    echo Invalid option, please try again.
    pause
    goto getinput
)

if "%choice%"=="1" (
    goto register
) else if "%choice%"=="2" (
    goto unregister
) else if "%choice%"=="3" (
    goto exit
) else (
    echo Invalid option, please try again.
    pause
    goto getinput
)

:register
cls
echo Registering context menu...

:: Check if Python is available
where python >nul 2>nul
if errorlevel 1 (
    echo Error: Python not found. Please make sure Python is installed and added to PATH.
    pause
    goto menu
)

:: Execute register command
python "%~dp0main.py" --register
if errorlevel 1 (
    echo Registration failed!
) else (
    echo Registration completed successfully!
)
pause
goto menu

:unregister
cls
echo Unregistering context menu...

:: Check if Python is available
where python >nul 2>nul
if errorlevel 1 (
    echo Error: Python not found. Please make sure Python is installed and added to PATH.
    pause
    goto menu
)

:: Execute unregister command
python "%~dp0main.py" --unregister
if errorlevel 1 (
    echo Unregistration failed!
) else (
    echo Unregistration completed successfully!
)
pause
goto menu

:exit
echo Thank you for using File Note Tool!
pause
exit /b 0