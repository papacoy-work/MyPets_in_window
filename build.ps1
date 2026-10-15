$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    $pythonPath = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
    if (-not (Test-Path -LiteralPath $pythonPath)) {
        throw 'Create .venv and install requirements-build.txt first.'
    }
    & $pythonPath -m PyInstaller --noconfirm --onefile --windowed --name MyPets --add-data 'pets;pets' pet.py
    if ($LASTEXITCODE -ne 0) { throw 'Executable build failed.' }
    Write-Host 'Distribution: dist/MyPets.exe'
} finally {
    Pop-Location
}
