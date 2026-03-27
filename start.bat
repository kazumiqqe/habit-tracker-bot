@echo off
chcp 65001 >nul
title Habit Tracker Bot Launcher

echo ================================
echo    Запуск Telegram Бота (Habit Tracker)
echo ================================
echo.

cd /d "%~dp0"

if not exist ".env" (
    echo [ОШИБКА] Файл .env не найден!
    echo Создайте файл .env с токеном бота в формате: BOT_TOKEN=ваш_токен
    echo.
    pause
    exit /b 1
)

if not exist "bot.py" (
    echo [ОШИБКА] Файл bot.py не найден!
    echo Убедитесь, что файл находится в той же папке
    echo.
    pause
    exit /b 1
)

echo [INFO] Проверка виртуального окружения...
if exist "venv\Scripts\activate.bat" (
    echo [OK] Виртуальное окружение найдено
    call venv\Scripts\activate.bat
) else (
    echo [WARNING] Виртуальное окружение не найдено
    echo Используется глобальный Python
)

echo.
echo [INFO] Запуск бота...
echo [INFO] Для остановки нажмите Ctrl+C
echo ================================
echo.

python bot.py

if errorlevel 1 (
    echo.
    echo ================================
    echo [ОШИБКА] Бот завершился с ошибкой!
    echo ================================
    echo.
    pause
    exit /b 1
)

echo.
echo ================================
echo [INFO] Бот остановлен
echo ================================
pause