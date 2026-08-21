from __future__ import annotations

import json
import sys

from .models import DiscoveredApp, appx_candidate
from .powershell import run_powershell_json


class MsixProvider:
    source = "msix"

    def discover(self) -> list[DiscoveredApp]:
        if sys.platform != "win32":
            return []
        script = r"""
function Resolve-AppLogo([string]$location, [string]$relativePath) {
  if (-not $location -or -not $relativePath) { return $null }
  $relativePath = $relativePath -replace '/', '\'
  $exact = Join-Path $location $relativePath
  if (Test-Path -LiteralPath $exact -PathType Leaf) { return $exact }
  $directory = Split-Path $exact
  $baseName = [IO.Path]::GetFileNameWithoutExtension($exact)
  if (-not (Test-Path -LiteralPath $directory -PathType Container)) { return $null }
  $assets = Get-ChildItem -LiteralPath $directory -File -ErrorAction SilentlyContinue |
    Where-Object {
      $_.BaseName -like "$baseName*" -and
      $_.Extension -match '^\.(png|jpg|jpeg|ico)$' -and
      $_.Name -notmatch 'contrast-(black|white)'
    } |
    Sort-Object Length -Descending
  if ($assets) { return $assets[0].FullName }
  return $null
}

$packages = @{}
Get-AppxPackage -ErrorAction SilentlyContinue | ForEach-Object {
  $packages[$_.PackageFamilyName] = $_
}
$result = foreach ($entry in (Get-StartApps -ErrorAction SilentlyContinue)) {
  if ($entry.AppID -notmatch '!') { continue }
  $parts = $entry.AppID.Split('!', 2)
  $package = $packages[$parts[0]]
  $icon = $null
  if ($package) {
    try {
      $manifest = Get-AppxPackageManifest -Package $package
      $application = $manifest.Package.Applications.Application |
        Where-Object { $_.Id -eq $parts[1] } | Select-Object -First 1
      if ($application) {
        $logo = $application.VisualElements.Square44x44Logo
        if (-not $logo) { $logo = $application.VisualElements.Square150x150Logo }
        $icon = Resolve-AppLogo $package.InstallLocation $logo
      }
    } catch {}
  }
  [pscustomobject]@{
    Name = $entry.Name
    AppID = $entry.AppID
    Icon = $icon
  }
}
$result | ConvertTo-Json -Compress
"""
        try:
            raw = run_powershell_json(script, timeout=45)
        except (OSError, UnicodeError, json.JSONDecodeError):
            return []
        entries = raw if isinstance(raw, list) else [raw]
        result_apps = []
        for item in entries:
            if not isinstance(item, dict):
                continue
            candidate = appx_candidate(
                name=str(item.get("Name", "")),
                app_user_model_id=str(item.get("AppID", "")),
                icon=str(item.get("Icon") or "") or None,
                source=self.source,
            )
            if candidate:
                result_apps.append(candidate)
        return result_apps
