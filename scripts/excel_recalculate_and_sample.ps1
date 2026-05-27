param(
    [Parameter(Mandatory = $true)]
    [string]$Workbook,

    [Parameter(Mandatory = $true)]
    [string]$Worksheet,

    [Parameter(Mandatory = $true)]
    [string[]]$Cells
)

$ErrorActionPreference = "Stop"

function Release-ComObject {
    param([object]$Object)
    if ($null -ne $Object) {
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($Object)
    }
}

function Convert-ValueToText {
    param([object]$Value)
    if ($null -eq $Value) {
        return "<missing>"
    }
    return [string]$Value
}

$excel = $null
$workbookObject = $null
$worksheetObject = $null
$oldDisplayAlerts = $null
$oldAskToUpdateLinks = $null
$oldAutomationSecurity = $null

try {
    $fullPath = (Resolve-Path -LiteralPath $Workbook).Path

    $excel = New-Object -ComObject Excel.Application
    $oldDisplayAlerts = $excel.DisplayAlerts
    $oldAskToUpdateLinks = $excel.AskToUpdateLinks
    $oldAutomationSecurity = $excel.AutomationSecurity

    $excel.Visible = $false
    $excel.DisplayAlerts = $false
    $excel.AskToUpdateLinks = $false
    $excel.AutomationSecurity = 3

    $workbookObject = $excel.Workbooks.Open($fullPath, 0, $true)
    $excel.CalculateFullRebuild()

    if ($Worksheet -match '^\d+$') {
        $worksheetObject = $workbookObject.Worksheets.Item([int]$Worksheet)
    }
    else {
        $worksheetObject = $workbookObject.Worksheets.Item($Worksheet)
    }

    foreach ($cellRef in $Cells) {
        $value = $worksheetObject.Range($cellRef).Value2
        Write-Output ("{0}={1}" -f $cellRef, (Convert-ValueToText $value))
    }
}
finally {
    if ($null -ne $workbookObject) {
        $workbookObject.Close($false) | Out-Null
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

    Release-ComObject $worksheetObject
    Release-ComObject $workbookObject
    Release-ComObject $excel

    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
}
