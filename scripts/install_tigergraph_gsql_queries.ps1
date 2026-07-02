$ErrorActionPreference = "Stop"

Write-Host "Installing schema..."
gsql gsql/schema/iperform_enterprise_schema.gsql

Write-Host "Installing queries..."
Get-ChildItem gsql/queries/*.gsql | ForEach-Object {
  Write-Host "Installing $($_.FullName)"
  gsql $_.FullName
}

Write-Host "Installing loading job..."
gsql gsql/loading/production_loading_job.gsql

Write-Host "TigerGraph GSQL installation complete."
