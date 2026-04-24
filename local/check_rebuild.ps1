# Exits with code 1 if frontend needs rebuilding, 0 if the existing build is current.
# Called by local/Start.bat.

$build = 'frontend\build\index.html'
if (-not (Test-Path $build)) { exit 1 }

$buildTime = (Get-Item $build).LastWriteTime
$newestSrc = (Get-ChildItem 'frontend\src', 'frontend\public', 'frontend\package.json' -Recurse -File -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1).LastWriteTime

if ($null -eq $newestSrc) { exit 0 }
if ($newestSrc -gt $buildTime) { exit 1 } else { exit 0 }
