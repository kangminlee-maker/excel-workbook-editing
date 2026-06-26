param(
    [Parameter(Mandatory = $true)]
    [string]$TargetWorkbook,

    [Parameter(Mandatory = $true)]
    [string]$TemplateWorkbook,

    [Parameter(Mandatory = $true)]
    [string]$TemplateSheetName,

    [Parameter(Mandatory = $false)]
    [string]$FormulaMap = ""
)

$ErrorActionPreference = "Stop"

function Release-ComObject {
    param([object]$Object)
    if ($null -ne $Object) {
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($Object)
    }
}

$excel = $null
$targetWorkbookObject = $null
$templateWorkbookObject = $null
$sourceWorksheet = $null
$lastTargetWorksheet = $null
$copiedWorksheet = $null
$oldDisplayAlerts = $null
$oldAskToUpdateLinks = $null
$oldAutomationSecurity = $null

try {
    $targetPath = (Resolve-Path -LiteralPath $TargetWorkbook).Path
    $templatePath = (Resolve-Path -LiteralPath $TemplateWorkbook).Path

    $excel = New-Object -ComObject Excel.Application
    $oldDisplayAlerts = $excel.DisplayAlerts
    $oldAskToUpdateLinks = $excel.AskToUpdateLinks
    $oldAutomationSecurity = $excel.AutomationSecurity

    $excel.Visible = $false
    $excel.DisplayAlerts = $false
    $excel.AskToUpdateLinks = $false
    $excel.AutomationSecurity = 3

    $targetWorkbookObject = $excel.Workbooks.Open($targetPath, 0, $false)
    $templateWorkbookObject = $excel.Workbooks.Open($templatePath, 0, $true)
    $sourceWorksheet = $templateWorkbookObject.Worksheets.Item($TemplateSheetName)
    $lastTargetWorksheet = $targetWorkbookObject.Worksheets.Item($targetWorkbookObject.Worksheets.Count)

    $sourceWorksheet.Copy($null, $lastTargetWorksheet)
    $copiedWorksheet = $targetWorkbookObject.Worksheets.Item($TemplateSheetName)
    if (-not [string]::IsNullOrWhiteSpace($FormulaMap) -and (Test-Path -LiteralPath $FormulaMap)) {
        foreach ($line in Get-Content -LiteralPath $FormulaMap -Encoding UTF8) {
            if ([string]::IsNullOrWhiteSpace($line)) {
                continue
            }
            $parts = $line.Split("`t", 2)
            if ($parts.Count -ge 2) {
                $copiedWorksheet.Range($parts[0]).Formula = $parts[1]
            }
        }
    }
    $targetWorkbookObject.Save()

    Write-Output "copied"
}
finally {
    if ($null -ne $templateWorkbookObject) {
        $templateWorkbookObject.Close($false) | Out-Null
    }
    if ($null -ne $targetWorkbookObject) {
        $targetWorkbookObject.Close($true) | Out-Null
    }

    if ($null -ne $excel) {
        if ($null -ne $oldDisplayAlerts) {
            $excel.DisplayAlerts = $oldDisplayAlerts
        }
        if ($null -ne $oldAskToUpdateLinks) {
            $excel.AskToUpdateLinks = $oldAskToUpdateLinks
        }
        if ($null -ne $oldAutomationSecurity) {
            $excel.AutomationSecurity = $oldAutomationSecurity
        }
        $excel.Quit()
    }

    Release-ComObject $lastTargetWorksheet
    Release-ComObject $copiedWorksheet
    Release-ComObject $sourceWorksheet
    Release-ComObject $templateWorkbookObject
    Release-ComObject $targetWorkbookObject
    Release-ComObject $excel

    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
}
