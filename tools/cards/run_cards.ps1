# PowerShell entry for the card runner: finds Git Bash and the claude CLI, then calls run_cards.sh.
# Usage (repo root):  powershell -ExecutionPolicy Bypass -File .\tools\cards\run_cards.ps1 T01 T02
$ErrorActionPreference = "Stop"

$bash = @(
    "C:\Program Files\Git\bin\bash.exe",
    "C:\Program Files (x86)\Git\bin\bash.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $bash) { throw "Git Bash not found" }

if (-not $env:CLAUDE_BIN) {
    $onPath = Get-Command claude -ErrorAction SilentlyContinue
    if ($onPath) {
        $env:CLAUDE_BIN = $onPath.Source
    } else {
        $newest = Get-ChildItem "$env:APPDATA\Claude\claude-code\*\*\claude.exe" -ErrorAction SilentlyContinue |
            Sort-Object { [version]($_.Directory.Parent.Name) } | Select-Object -Last 1
        if (-not $newest) { throw "claude CLI not found; set CLAUDE_BIN" }
        $env:CLAUDE_BIN = $newest.FullName
    }
}
Write-Host "claude: $env:CLAUDE_BIN"

& $bash "tools/cards/run_cards.sh" @args
exit $LASTEXITCODE
