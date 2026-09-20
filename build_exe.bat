@echo off
chcp 65001 > nul
title HWP Toolkit - EXE 빌드 스크립트

echo ======================================================================
echo   한글 문서 통합 관리자 (HWP Toolkit) - Windows EXE 빌드 시작
echo ======================================================================
echo.

echo [1/3] 기존 빌드 캐시 및 임시 파일 정리 중...
if exist "build" rd /s /q "build"
if exist "dist\HWP_Toolkit.exe" del /f /q "dist\HWP_Toolkit.exe"

echo.
echo [2/3] PyInstaller를 통한 단일 실행 파일(EXE) 생성 중...
echo (콘솔 창 숨김 모드 --windowed, 단일 파일 --onefile)
echo.

python -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onefile ^
    --windowed ^
    --name "HWP_Toolkit" ^
    --hidden-import win32com.client ^
    --hidden-import pyhwpx ^
    --hidden-import pythoncom ^
    main_gui.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [오류] EXE 빌드 도중 문제가 발생했습니다. 에러 메시지를 확인하세요.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ======================================================================
echo [3/3] 빌드 성공 완료!
echo  -> 실행 파일 위치: dist\HWP_Toolkit.exe
echo  -> 이 파일을 원하는 곳(바탕화면 등)으로 복사하여 더블 클릭으로 실행하세요.
echo ======================================================================
echo.
pause
