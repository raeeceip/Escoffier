@echo off
:: Escoffier Setup Script for Windows Command Prompt/Batch

echo 🍳 Escoffier Kitchen Simulation Platform Setup
echo =============================================

:: Check if Python is available
echo.
echo 1. Checking Python installation...
python --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%i in ('python --version') do echo ✅ Python found: %%i
) else (
    echo ❌ Python not found. Please install Python 3.11+ from https://python.org
    exit /b 1
)

:: Check for UV package manager
echo.
echo 2. Checking UV package manager...
set UV_INSTALLED=false
uv --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%i in ('uv --version') do echo ✅ UV found: %%i
    set UV_INSTALLED=true
) else (
    echo ⚠️  UV not found, will use pip instead
)

:: Create virtual environment and install dependencies
echo.
echo 3. Setting up dependencies...

if "%UV_INSTALLED%"=="true" (
    echo Installing with UV...
    uv sync
    if %errorlevel% neq 0 (
        echo ❌ UV sync failed, falling back to pip
        set UV_INSTALLED=false
    ) else (
        echo ✅ Dependencies installed with UV
    )
)

if "%UV_INSTALLED%"=="false" (
    echo Installing with pip...
    
    :: Create virtual environment
    python -m venv .venv
    
    :: Activate virtual environment
    call .venv\Scripts\activate.bat
    
    :: Upgrade pip
    python -m pip install --upgrade pip
    
    :: Install dependencies
    python -m pip install -r requirements.txt
    if %errorlevel% equ 0 (
        echo ✅ Dependencies installed with pip
    ) else (
        echo ❌ Failed to install dependencies
        exit /b 1
    )
)

:: Create data directories
echo.
echo 4. Creating data directories...
for %%d in ("data" "data\analytics" "data\analytics\charts" "data\analytics\reports" "data\metrics") do (
    if not exist %%d (
        mkdir %%d
        echo ✅ Created directory: %%d
    ) else (
        echo ✅ Directory exists: %%d
    )
)

:: Copy configuration template
echo.
echo 5. Setting up configuration...
if not exist "configs\config.yaml" (
    if exist "configs\config.yaml.example" (
        copy "configs\config.yaml.example" "configs\config.yaml" >nul
        echo ✅ Configuration template copied
        echo ⚠️  Please edit configs\config.yaml to add your API keys
    ) else (
        echo ⚠️  No configuration template found
    )
) else (
    echo ✅ Configuration file already exists
)

:: Initialize database
echo.
echo 6. Initializing database...
if "%UV_INSTALLED%"=="true" (
    uv run python -m cli.main init_db
) else (
    .venv\Scripts\python.exe -m cli.main init_db
)

if %errorlevel% equ 0 (
    echo ✅ Database initialized
) else (
    echo ❌ Database initialization failed
)

:: Success message
echo.
echo 🎉 Setup Complete!
echo ==================
echo.
echo Next steps:
echo 1. Edit configs\config.yaml to add your LLM API keys
echo 2. Create your first agent:
if "%UV_INSTALLED%"=="true" (
    echo    uv run python -m cli.main create_agent "Chef Gordon" head_chef "leadership,knife_skills"
) else (
    echo    .venv\Scripts\python.exe -m cli.main create_agent "Chef Gordon" head_chef "leadership,knife_skills"
)
echo 3. Run a scenario:
if "%UV_INSTALLED%"=="true" (
    echo    uv run python -m cli.main run_scenario cooking_challenge
) else (
    echo    .venv\Scripts\python.exe -m cli.main run_scenario cooking_challenge
)
echo 4. View metrics:
if "%UV_INSTALLED%"=="true" (
    echo    uv run python -m cli.main metrics --export_csv --generate_charts
) else (
    echo    .venv\Scripts\python.exe -m cli.main metrics --export_csv --generate_charts
)
echo.
echo For more commands, run:
if "%UV_INSTALLED%"=="true" (
    echo    uv run python -m cli.main --help
) else (
    echo    .venv\Scripts\python.exe -m cli.main --help
)
echo.
echo Happy cooking! 👨‍🍳🤖

pause