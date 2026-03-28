@echo off
chcp 65001 >nul
echo ==========================================
echo Quantum Switch Windows Build Script
echo ==========================================
echo.

:: Check if npm is installed
where npm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm not found!
    echo Please install Node.js first: https://nodejs.org/
    exit /b 1
)

:: Build frontend
echo [INFO] Building frontend...
cd frontend

:: Install dependencies if node_modules doesn't exist
if not exist "node_modules" (
    echo [INFO] Installing frontend dependencies...
    call npm install
    if errorlevel 1 (
        echo [ERROR] Failed to install frontend dependencies!
        exit /b 1
    )
)

:: Build frontend
call npm run build
if errorlevel 1 (
    echo [ERROR] Frontend build failed!
    exit /b 1
)

cd ..
echo [INFO] Frontend build completed!
echo.

:: Check if frontend dist exists (double check)
if not exist "frontend\dist" (
    echo [ERROR] Frontend dist not found after build!
    exit /b 1
)

:: Check Python
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    echo Please install Python 3.11+ from https://python.org/
    exit /b 1
)

for /f "tokens=*" %%a in ('python --version') do (
    echo [INFO] Found %%a
)

:: Create virtual environment if not exists
echo [INFO] Setting up virtual environment...
if not exist ".venv" (
    echo [INFO] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment!
        exit /b 1
    )
)

:: Activate virtual environment
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment!
    exit /b 1
)

for /f "tokens=*" %%a in ('where python') do (
    echo [INFO] Using Python: %%a
)

:: Install/Upgrade pip
echo [INFO] Upgrading pip...
python -m pip install --upgrade pip >nul 2>&1

:: Install backend dependencies
echo [INFO] Installing backend dependencies...
cd backend
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install backend dependencies!
    exit /b 1
)

:: Install PyInstaller
echo [INFO] Installing PyInstaller...
python -m pip install pyinstaller >nul 2>&1

:: Clean previous build
echo [INFO] Cleaning previous build...
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul

:: Run PyInstaller
echo [INFO] Building executable...
python -m PyInstaller build.spec

if errorlevel 1 (
    echo [ERROR] Build failed!
    exit /b 1
)

:: Create output structure
echo [INFO] Creating output structure...
mkdir "dist\QuantumSwitch\config" 2>nul
mkdir "dist\QuantumSwitch\logs" 2>nul

:: Copy executable
copy "dist\QuantumSwitch.exe" "dist\QuantumSwitch\"

:: Copy config template
copy ".env" "dist\QuantumSwitch\config\.env.template"

:: Copy data files (only vanilla)
echo [INFO] Copying data files...
xcopy "data\vanilla" "dist\QuantumSwitch\data\vanilla\" /s /i /y

:: Copy frontend dist to bundled app
@REM echo [INFO] Copying frontend files...
@REM xcopy "..\frontend\dist" "dist\QuantumSwitch\frontend\" /s /i /y

:: Copy icon to bundled app root
echo [INFO] Copying icon file...
copy "icon.ico" "dist\QuantumSwitch\"

:: Copy readme
echo [INFO] Copying readme...
copy "..\README*" "dist\QuantumSwitch\" 2>nul

echo.
echo ==========================================
echo Build completed successfully!
echo Output: backend/dist/QuantumSwitch/
echo ==========================================
echo.
echo Next steps:
echo 1. Edit backend/dist/QuantumSwitch/config/.env.template
echo 2. Rename it to .env
echo 3. Set your GAME_MODS_DIRECTORY path
echo 4. Run QuantumSwitch.exe
echo.
echo NOTE: If QR code displays incorrectly in console,
echo       right-click the title bar -^> Properties -^> Font,
echo       and select a font like "Consolas".
echo.
pause
