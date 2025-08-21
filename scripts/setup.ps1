# Escoffier Setup Script for Windows PowerShell

Write-Host "🍳 Escoffier Kitchen Simulation Platform Setup" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green

# Check if Python is available
Write-Host "`n1. Checking Python installation..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Python found: $pythonVersion" -ForegroundColor Green
    } else {
        throw "Python not found"
    }
} catch {
    Write-Host "❌ Python not found. Please install Python 3.11+ from https://python.org" -ForegroundColor Red
    exit 1
}

# Check for UV package manager
Write-Host "`n2. Checking UV package manager..." -ForegroundColor Yellow
$uvInstalled = $false
try {
    $uvVersion = uv --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ UV found: $uvVersion" -ForegroundColor Green
        $uvInstalled = $true
    }
} catch {
    Write-Host "⚠️  UV not found, will use pip instead" -ForegroundColor Yellow
}

# Create virtual environment and install dependencies
Write-Host "`n3. Setting up dependencies..." -ForegroundColor Yellow

if ($uvInstalled) {
    Write-Host "Installing with UV..." -ForegroundColor Blue
    uv sync
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ UV sync failed, falling back to pip" -ForegroundColor Red
        $uvInstalled = $false
    } else {
        Write-Host "✅ Dependencies installed with UV" -ForegroundColor Green
    }
}

if (-not $uvInstalled) {
    Write-Host "Installing with pip..." -ForegroundColor Blue
    
    # Create virtual environment
    python -m venv .venv
    
    # Activate virtual environment
    & .\.venv\Scripts\Activate.ps1
    
    # Upgrade pip
    python -m pip install --upgrade pip
    
    # Install dependencies
    python -m pip install -r requirements.txt
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Dependencies installed with pip" -ForegroundColor Green
    } else {
        Write-Host "❌ Failed to install dependencies" -ForegroundColor Red
        exit 1
    }
}

# Create data directories
Write-Host "`n4. Creating data directories..." -ForegroundColor Yellow
$dataDirs = @("data", "data/analytics", "data/analytics/charts", "data/analytics/reports", "data/metrics")
foreach ($dir in $dataDirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "✅ Created directory: $dir" -ForegroundColor Green
    } else {
        Write-Host "✅ Directory exists: $dir" -ForegroundColor Green
    }
}

# Copy configuration template
Write-Host "`n5. Setting up configuration..." -ForegroundColor Yellow
if (-not (Test-Path "configs/config.yaml")) {
    if (Test-Path "configs/config.yaml.example") {
        Copy-Item "configs/config.yaml.example" "configs/config.yaml"
        Write-Host "✅ Configuration template copied" -ForegroundColor Green
        Write-Host "⚠️  Please edit configs/config.yaml to add your API keys" -ForegroundColor Yellow
    } else {
        Write-Host "⚠️  No configuration template found" -ForegroundColor Yellow
    }
} else {
    Write-Host "✅ Configuration file already exists" -ForegroundColor Green
}

# Initialize database
Write-Host "`n6. Initializing database..." -ForegroundColor Yellow
if ($uvInstalled) {
    uv run python -m cli.main init_db
} else {
    & .\.venv\Scripts\python.exe -m cli.main init_db
}

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Database initialized" -ForegroundColor Green
} else {
    Write-Host "❌ Database initialization failed" -ForegroundColor Red
}

# Success message
Write-Host "`n🎉 Setup Complete!" -ForegroundColor Green
Write-Host "==================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Edit configs/config.yaml to add your LLM API keys" -ForegroundColor White
Write-Host "2. Create your first agent:" -ForegroundColor White
if ($uvInstalled) {
    Write-Host "   uv run python -m cli.main create_agent 'Chef Gordon' head_chef 'leadership,knife_skills'" -ForegroundColor Gray
} else {
    Write-Host "   .\.venv\Scripts\python.exe -m cli.main create_agent 'Chef Gordon' head_chef 'leadership,knife_skills'" -ForegroundColor Gray
}
Write-Host "3. Run a scenario:" -ForegroundColor White
if ($uvInstalled) {
    Write-Host "   uv run python -m cli.main run_scenario cooking_challenge" -ForegroundColor Gray
} else {
    Write-Host "   .\.venv\Scripts\python.exe -m cli.main run_scenario cooking_challenge" -ForegroundColor Gray
}
Write-Host "4. View metrics:" -ForegroundColor White
if ($uvInstalled) {
    Write-Host "   uv run python -m cli.main metrics --export_csv --generate_charts" -ForegroundColor Gray
} else {
    Write-Host "   .\.venv\Scripts\python.exe -m cli.main metrics --export_csv --generate_charts" -ForegroundColor Gray
}
Write-Host ""
Write-Host "For more commands, run:" -ForegroundColor Cyan
if ($uvInstalled) {
    Write-Host "   uv run python -m cli.main --help" -ForegroundColor Gray
} else {
    Write-Host "   .\.venv\Scripts\python.exe -m cli.main --help" -ForegroundColor Gray
}
Write-Host ""
Write-Host "Happy cooking! 👨‍🍳🤖" -ForegroundColor Green