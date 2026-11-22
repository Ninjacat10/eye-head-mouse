<#
  Eye + Head Mouse - installer
  Creates a Python virtual environment, installs dependencies, and adds
  Desktop + Start Menu shortcuts. Requires Python 3.12 (3.10-3.12 work).

  Usage (from the project folder):
      powershell -ExecutionPolicy Bypass -File install.ps1
#>
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

function Find-Python {
    foreach ($v in "3.12", "3.11", "3.10") {
        try { $exe = & py "-$v" -c "import sys; print(sys.executable)" 2>$null; if ($LASTEXITCODE -eq 0 -and $exe) { return $exe.Trim() } } catch {}
    }
    return $null
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    $py = Find-Python
    if (-not $py) {
        Write-Host "Python 3.10-3.12 not found. Install it from https://www.python.org/downloads/release/python-3128/ and re-run." -ForegroundColor Red
        exit 1
    }
    Write-Host "Creating virtual environment with $py"
    & $py -m venv .venv
}

Write-Host "Installing dependencies (a few minutes the first time)..."
& .venv\Scripts\python.exe -m pip install --upgrade pip --quiet
& .venv\Scripts\python.exe -m pip install -r requirements.txt --quiet

$shell = New-Object -ComObject WScript.Shell
$targets = @(
    [Environment]::GetFolderPath("Desktop"),
    (Join-Path ([Environment]::GetFolderPath("Programs")) "")
)
foreach ($dir in $targets) {
    $lnk = $shell.CreateShortcut((Join-Path $dir "Eye + Head Mouse.lnk"))
    $lnk.TargetPath = "$env:WINDIR\System32\wscript.exe"
    $lnk.Arguments = "`"$root\launch.vbs`""
    $lnk.WorkingDirectory = $root
    $lnk.IconLocation = "$root\assets\icon.ico"
    $lnk.Description = "Hands-free mouse: head/eye pointing with gesture clicks"
    $lnk.Save()
}
Write-Host "Done! Launch 'Eye + Head Mouse' from your Desktop or Start Menu." -ForegroundColor Green
