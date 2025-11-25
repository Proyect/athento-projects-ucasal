Param(
    [switch]$Build
)

$scriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Resolve-Path (Join-Path $scriptDirectory "..")

Set-Location $projectRoot

if ($Build.IsPresent) {
    docker compose up --build -d
} else {
    docker compose up -d
}


