$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    $pythonPath = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
    if (-not (Test-Path -LiteralPath $pythonPath)) {
        throw 'Create .venv and install requirements-build.txt first.'
    }
    & $pythonPath -m PyInstaller --noconfirm --onefile --windowed --name MyPets --add-data 'pets;pets' pet.py
    if ($LASTEXITCODE -ne 0) { throw 'Executable build failed.' }
    try {
        Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'dist/MyPets.exe') -Destination (Join-Path $PSScriptRoot 'MyPets.exe') -ErrorAction Stop
    } catch {
        throw 'Built dist/MyPets.exe. Close the running MyPets app before copying it to MyPets.exe in the project root.'
    }
    Write-Host 'Distribution: MyPets.exe (also in dist/MyPets.exe)'
} finally {
    Pop-Location
}
