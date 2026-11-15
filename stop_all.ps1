# FaceClass System Shutdown Script (PowerShell)
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "         FaceClass System Shutdown (PowerShell)    " -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host ""

$Ports = @(5000, 5173)
$Stopped = 0

foreach ($Port in $Ports) {
    try {
        $Connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        if ($Connections) {
            foreach ($Conn in $Connections) {
                $ProcId = $Conn.OwningProcess
                $Proc = Get-Process -Id $ProcId -ErrorAction SilentlyContinue
                if ($Proc) {
                    Write-Host "Stopping process $($Proc.ProcessName) (PID: $ProcId) listening on port $Port..." -ForegroundColor Yellow
                    Stop-Process -Id $ProcId -Force -ErrorAction SilentlyContinue
                    $Stopped++
                }
            }
        }
    } catch {
        # ignore lookup errors
    }
}

if ($Stopped -eq 0) {
    Write-Host "No active FaceClass processes found on ports 5000 or 5173." -ForegroundColor Green
} else {
    Write-Host "Successfully stopped $Stopped process(es)." -ForegroundColor Green
}

Write-Host ""
