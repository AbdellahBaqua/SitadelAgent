# Fetch Yvelines (DEP_CODE=78) housing authorisations from the SDES DiDo API,
# in small sequential pages (100 rows) to avoid the connection resets seen on full exports.
param(
  [string]$Dep = "78",
  [string]$Rid = "8b35affb-55fc-4c1f-915b-7750f974446a",
  [string]$Millesime = "2026-10",
  [int]$PageSize = 100,
  [string]$Columns = "",   # optional comma list, e.g. "COMM,TYPE_DAU,NUM_DAU,NB_LGT_TOT_CREES"
  [string]$Out = "$PSScriptRoot\..\data\yvelines_logements_$Dep.json"
)
$ErrorActionPreference = "Stop"
$base = "https://data.statistiques.developpement-durable.gouv.fr/dido/api/v1/datafiles/$Rid/rows"
$all = New-Object System.Collections.Generic.List[object]
$page = 1; $total = $null
do {
  $url = "${base}?millesime=$Millesime&pageSize=$PageSize&page=$page&DEP_CODE=eq:$Dep"
  if ($Columns) { $url += "&columns=$Columns" }
  $r = $null
  for ($try = 1; $try -le 5 -and -not $r; $try++) {
    try { $r = Invoke-RestMethod $url -TimeoutSec 120 }
    catch { Write-Host "page $page try $try failed: $($_.Exception.Message)"; Start-Sleep -Seconds (3 * $try) }
  }
  if (-not $r) { throw "page $page failed after 5 tries" }
  if ($null -eq $total) { $total = $r.total; Write-Host "total rows: $total" }
  foreach ($row in $r.data) { $all.Add($row) }
  Write-Host "page $page -> $($all.Count)/$total"
  $page++
  Start-Sleep -Milliseconds 300
} while ($all.Count -lt $total -and $r.data.Count -gt 0)
$all | ConvertTo-Json -Depth 5 | Set-Content -Encoding utf8 $Out
Write-Host "saved $($all.Count) rows to $Out"
