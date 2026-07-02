$ErrorActionPreference = "Stop"

Write-Host "Installing TigerGraph source of truth: tigergraph/"
gsql tigergraph/schema/phx_dm_iperform_enterprise_schema.gsql

Get-ChildItem tigergraph/queries_v1/*.gsql | ForEach-Object {
  Write-Host "Installing query: $($_.FullName)"
  gsql $_.FullName
}

Write-Host "Installing loading job..."
gsql tigergraph/loading/phx_dm_production_loading_job.gsql

Write-Host "TigerGraph source-of-truth install complete."
