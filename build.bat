@echo off
chcp 65001 >nul
echo ==========================================
echo Quantum Selector Windows Build Script
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

cd backend

:: Activate virtual environment
echo [INFO] Activating virtual environment...
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo [WARNING] Virtual environment not found, using system Python
)

:: Verify Python path
for /f "tokens=*" %%a in ('where python') do (
    echo [INFO] Using Python: %%a
    goto :python_done
)
:python_done

:: Install PyInstaller if not exists
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing PyInstaller...
    pip install pyinstaller
)

:: Clean previous build
echo [INFO] Cleaning previous build...
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul

:: Run PyInstaller
echo [INFO] Building executable...
pyinstaller build.spec

if errorlevel 1 (
    echo [ERROR] Build failed!
    exit /b 1
)

:: Create output structure
echo [INFO] Creating output structure...
mkdir "dist\QuantumSelector\config" 2>nul
mkdir "dist\QuantumSelector\logs" 2>nul

:: Copy executable
copy "dist\QuantumSelector.exe" "dist\QuantumSelector\"

:: Copy config template
copy ".env" "dist\QuantumSelector\config\.env.template"

:: Copy data files
xcopy "data" "dist\QuantumSelector\data" /s /i /y

echo.
echo ==========================================
echo Build completed successfully!
echo Output: backend/dist/QuantumSelector/
echo ==========================================
echo.
echo Next steps:
echo 1. Edit backend/dist/QuantumSelector/config/.env.template
echo 2. Rename it to .env
echo 3. Set your GAME_MODS_DIRECTORY path
echo 4. Run QuantumSelector.exe
echo.
pause
