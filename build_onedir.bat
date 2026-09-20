@echo off
chcp 65001 > nul
title HWP Toolkit - 폴더형(Onedir) 초고속 실행 EXE 빌드

echo ======================================================================
echo   한글 문서 통합 관리자 (HWP Toolkit) - 폴더형(Onedir) 빌드 시작
echo ======================================================================
echo.

python -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onedir ^
    --windowed ^
    --name "HWP_Toolkit" ^
    --hidden-import win32com.client ^
    --hidden-import pyhwpx ^
    --hidden-import pythoncom ^
    main_gui.py

if %ERRORLEVEL% NEQ 0 (
    echo [오류] 빌드 실패.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo 빌드 성공! dist\HWP_Toolkit\HWP_Toolkit.exe 에서 바로 실행 가능합니다.
pause
