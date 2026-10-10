# Show what the running card session is doing, without spending usage.
# Reads the newest transcript of this repo that started with "Run the task card" and prints its last tool calls.
# Usage (repo root): .\tools\cards\watch.ps1 [-Follow] [-Last 15]
param([switch]$Follow, [int]$Last = 15)

$slug = (Get-Location).Path -replace "[:\\/]", "-"
$dir = Join-Path $env:USERPROFILE ".claude\projects\$slug"

function Show-Card {
    $t = Get-ChildItem $dir -Filter *.jsonl -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Where-Object { (Get-Content $_.FullName -TotalCount 8 -Encoding UTF8) -match "Run the task card" } |
        Select-Object -First 1
    if (-not $t) { Write-Host "no card transcript found in $dir"; return }
    $m = Get-Content $t.FullName -TotalCount 8 -Encoding UTF8 | Select-String -Pattern "Run the task card (\S+?)\." |
        Select-Object -First 1
    $name = if ($m) { $m.Matches[0].Groups[1].Value } else { $t.Name }
    Write-Host ("== {0}  (updated {1:HH:mm:ss})" -f $name, $t.LastWriteTime)
    $calls = foreach ($line in Get-Content $t.FullName -Encoding UTF8) {
        try { $e = $line | ConvertFrom-Json } catch { continue }
        if ($e.type -ne "assistant") { continue }
        foreach ($c in $e.message.content) {
            if ($c.type -eq "tool_use") {
                $arg = if ($c.input.command) { $c.input.command } elseif ($c.input.file_path) { $c.input.file_path } else { "" }
                $arg = ($arg -replace "\s+", " ")
                if ($arg.Length -gt 110) { $arg = $arg.Substring(0, 110) + "..." }
                "{0,-6} {1}" -f $c.name, $arg
            }
        }
    }
    $calls | Select-Object -Last $Last | ForEach-Object { Write-Host "  $_" }
    Write-Host "-- uncommitted:"
    git status --short | ForEach-Object { Write-Host "  $_" }
}

do {
    if ($Follow) { Clear-Host }
    Show-Card
    if ($Follow) { Start-Sleep -Seconds 5 }
} while ($Follow)
