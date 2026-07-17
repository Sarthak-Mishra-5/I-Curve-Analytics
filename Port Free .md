# 1. Find what's holding the port
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object LocalPort, State, OwningProcess -Unique

# 2. Identify the process before killing it (sanity check it's really your stale backend/frontend, not something else)
Get-Process -Id <OwningProcess> | Select-Object Id, ProcessName, StartTime, @{n='CmdLine';e={(Get-CimInstance Win32_Process -Filter "ProcessId=$($_.Id)").CommandLine}}

# 3. Kill it
Stop-Process -Id <OwningProcess> -Force

# 4. Confirm the port is free
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
