# runai installer for Windows
# Usage: irm https://raw.githubusercontent.com/malnadhudga/runai/main/install.ps1 | iex

$ErrorActionPreference = "Stop"

function Write-Step($msg) { Write-Host "`n>> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "   $msg" -ForegroundColor Green }
function Write-Fail($msg) { Write-Host "   ERROR: $msg" -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "  runai installer" -ForegroundColor Blue
Write-Host "  ----------------" -ForegroundColor Blue

# ── 1. Check / install Python ────────────────────────────────────────────────
Write-Step "Checking for Python 3.10+..."

$python = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($ver -match "Python 3\.(\d+)") {
            $minor = [int]$Matches[1]
            if ($minor -ge 10) {
                $python = $cmd
                Write-Ok "Found: $ver"
                break
            }
        }
    } catch {}
}

if (-not $python) {
    Write-Step "Python 3.10+ not found. Installing via winget..."
    try {
        winget install --id Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
        # Refresh PATH so python is available in this session
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                    [System.Environment]::GetEnvironmentVariable("Path", "User")
        $python = "python"
        Write-Ok "Python installed."
    } catch {
        Write-Fail "Could not install Python automatically. Please install Python 3.10+ from https://python.org and re-run this script."
    }
}

# ── 2. Upgrade pip ───────────────────────────────────────────────────────────
Write-Step "Upgrading pip..."
try {
    & $python -m pip install --upgrade pip --quiet
    Write-Ok "pip up to date."
} catch {
    Write-Fail "pip upgrade failed: $_"
}

# ── 3. Install runai ─────────────────────────────────────────────────────────
Write-Step "Installing runai..."
try {
    & $python -m pip install --upgrade runai --quiet
    Write-Ok "runai installed."
} catch {
    Write-Fail "pip install runai failed: $_"
}

# ── 4. Verify runai is on PATH ───────────────────────────────────────────────
Write-Step "Checking runai command..."

# Scripts folder may not be on PATH yet — find it and add if needed
$scriptsDir = & $python -c "import sysconfig; print(sysconfig.get_path('scripts'))" 2>$null
if ($scriptsDir -and (Test-Path $scriptsDir)) {
    $userPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
    if ($userPath -notlike "*$scriptsDir*") {
        [System.Environment]::SetEnvironmentVariable(
            "Path", "$userPath;$scriptsDir", "User"
        )
        $env:Path += ";$scriptsDir"
        Write-Ok "Added $scriptsDir to your PATH."
    }
}

$runaiCmd = Get-Command runai -ErrorAction SilentlyContinue
$runaiPath = if ($runaiCmd) { $runaiCmd.Source } else { $null }
if ($runaiPath) {
    Write-Ok "runai is ready at: $runaiPath"
} else {
    Write-Host ""
    Write-Host "  runai was installed but the command is not on PATH yet." -ForegroundColor Yellow
    Write-Host "  Please restart your terminal and try again." -ForegroundColor Yellow
}

# ── 5. .env setup reminder ───────────────────────────────────────────────────
Write-Host ""
Write-Host "  Done! Next steps:" -ForegroundColor Green
Write-Host ""
Write-Host "  1. Create a .env file in the folder you want to work from:"
Write-Host "        GEMINI_API_KEY=your-key-here"
Write-Host "     or OPENAI_API_KEY=your-key-here"
Write-Host ""
Write-Host "  2. Start the agent:"
Write-Host "        runai" -ForegroundColor Cyan
Write-Host ""
