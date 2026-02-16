Set-Location "c:/Users/basel/Downloads/open-webui git/open-webui"

$python = (Join-Path (Get-Location).Path ".venv311\\Scripts\\python.exe")
$backendDir = "c:/Users/basel/Downloads/open-webui git/open-webui/backend"
$sqliteDbUrl = "sqlite:///./test.db"

$reportPath = "c:/Users/basel/Downloads/open-webui git/open-webui/VALIDATION_REPORT_AGENT_WORKSPACE_AR.md"
$now = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$results = New-Object System.Collections.Generic.List[object]

function Add-Result {
  param([string]$Name,[string]$Status,[string]$Details)
  $results.Add([pscustomobject]@{ Check=$Name; Status=$Status; Details=$Details }) | Out-Null
}

function Run-Check {
  param([string]$Name,[scriptblock]$Script)
  try {
    $detail = & $Script
    Add-Result $Name "PASS" ($detail | Out-String).Trim()
  } catch {
    Add-Result $Name "FAIL" $_.Exception.Message
  }
}

Run-Check "open-webui endpoint (3001)" {
  $w = Invoke-WebRequest -Uri "http://localhost:3001" -UseBasicParsing -TimeoutSec 30
  "HTTP $($w.StatusCode)"
}

Run-Check "sidecar health (4000)" {
  $hRaw = (Invoke-WebRequest -Uri "http://localhost:4000/health" -UseBasicParsing -TimeoutSec 30).Content
  $h = $hRaw | ConvertFrom-Json
  "status=$($h.status), timeout=$($h.timeout_seconds), retries=$($h.max_retries)"
}

Run-Check "searxng endpoint (8081)" {
  $s = Invoke-WebRequest -Uri "http://localhost:8081" -UseBasicParsing -TimeoutSec 30
  "HTTP $($s.StatusCode)"
}

Run-Check "route wiring: tools/pipelines/retrieval" {
  $routersFile = "c:/Users/basel/Downloads/open-webui git/open-webui/backend/open_webui/bootstrap/routers.py"
  $retrievalFile = "c:/Users/basel/Downloads/open-webui git/open-webui/backend/open_webui/routers/retrieval.py"

  $mustHave = @(
    @{ file = $routersFile; pattern = 'include_router\(pipelines\.router, prefix="/api/v1/pipelines"' },
    @{ file = $routersFile; pattern = 'include_router\(tools\.router, prefix="/api/v1/tools"' },
    @{ file = $retrievalFile; pattern = '@router\.post\("/process/web/search"\)' },
    @{ file = $retrievalFile; pattern = '@router\.post\("/process/file"\)' }
  )

  foreach ($item in $mustHave) {
    $hit = Select-String -Path $item.file -Pattern $item.pattern
    if (-not $hit) {
      throw "Missing route wiring pattern: $($item.pattern)"
    }
  }

  "Verified wiring patterns in routers.py and retrieval.py"
}

Run-Check "external API call via sidecar chat" {
  $model = "google/gemini-3-flash-preview"
  $body = @{
    model = $model
    stream = $false
    messages = @(@{ role = "user"; content = "Reply with exactly: agent-workspace-validation-ok" })
  } | ConvertTo-Json -Depth 8

  $chatRaw = (Invoke-WebRequest -Uri "http://localhost:4000/v1/chat/completions" -Method POST -ContentType "application/json" -Body $body -UseBasicParsing -TimeoutSec 120).Content
  $chat = $chatRaw | ConvertFrom-Json
  $assistant = $chat.choices[0].message.content
  "model=$($chat.model), assistant='$assistant', total_tokens=$($chat.usage.total_tokens)"
}

Run-Check "local storage smoke (upload/get/delete)" {
  $cmd = @"
import io
import uuid
from pathlib import Path
from open_webui.storage.provider import LocalStorageProvider, UPLOAD_DIR

name = f"agent-workspace-{uuid.uuid4().hex}.txt"
provider = LocalStorageProvider()
contents, path = provider.upload_file(io.BytesIO(b"hello-storage"), name, {"scope":"validation"})
assert contents == b"hello-storage"
assert Path(path).exists()
resolved = provider.get_file(path)
assert Path(resolved).exists()
provider.delete_file(path)
assert not Path(path).exists()
print("storage_local_ok")
"@

  Push-Location $backendDir
  try {
    $env:PYTHONPATH = $backendDir
    $env:DATABASE_URL = $sqliteDbUrl
    $out = & $python -c $cmd
    if ($LASTEXITCODE -ne 0) { throw "local storage smoke failed" }
    $out
  } finally {
    Pop-Location
  }
}

Run-Check "governance and observability tests" {
  Push-Location $backendDir
  try {
    $env:PYTHONPATH = $backendDir
    $env:DATABASE_URL = $sqliteDbUrl
    $out = & $python -m pytest `
      open_webui/test/test_web_search_governance.py `
      open_webui/test/test_youtube_governance.py `
      open_webui/test/test_tool_governance.py `
      open_webui/test/test_openrouter_policy.py `
      open_webui/test/test_openrouter_observability.py -q

    if ($LASTEXITCODE -ne 0) {
      throw "pytest suite failed`n$out"
    }

    ($out | Out-String).Trim()
  } finally {
    Pop-Location
  }
}

$passCount = ($results | Where-Object { $_.Status -eq 'PASS' }).Count
$failCount = ($results | Where-Object { $_.Status -eq 'FAIL' }).Count

$lines = @()
$lines += "# تقرير التحقق الشامل — Agent Workspace"
$lines += ""
$lines += "- التاريخ: $now"
$lines += "- الملخص: PASS=$passCount / FAIL=$failCount"
$lines += "- ملاحظة: تم التحقق العملي من التشغيل + الأدوات + البحث + التخزين المحلي + الحوكمة + المراقبة."
$lines += ""
$lines += "## نتائج الفحوصات"
$lines += ""
$lines += "| الفحص | الحالة | التفاصيل |"
$lines += "|---|---|---|"
foreach ($r in $results) {
  $details = (($r.Details -replace "`r?`n", " ") -replace "\|", "/")
  $lines += "| $($r.Check) | $($r.Status) | $details |"
}

$lines += ""
$lines += "## قرار الاعتماد"
if ($failCount -eq 0) {
  $lines += ""
  $lines += "**GO** — البيئة جاهزة للتشغيل اليومي ضمن النطاق المحدد."
} else {
  $lines += ""
  $lines += "**NO-GO** — توجد فحوصات فاشلة تحتاج معالجة قبل الاعتماد الكامل."
}

Set-Content -Path $reportPath -Value ($lines -join "`r`n") -Encoding UTF8

Write-Output "Report written: $reportPath"
Write-Output "PASS=$passCount FAIL=$failCount"