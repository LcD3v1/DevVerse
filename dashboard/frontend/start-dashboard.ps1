param(
    [int]$Port = 3000
)

Set-Location -LiteralPath $PSScriptRoot
"Starting DevVerse dashboard on port $Port at $(Get-Date -Format o)" | Out-File -FilePath "dev-server-$Port.log" -Encoding utf8
npm.cmd run dev -- --hostname 127.0.0.1 --port $Port *>> "dev-server-$Port.log"
