on run argv
    local wb, wb2

    if (count of argv) < 3 then
        error "Usage: osascript excel_copy_sheet_into_workbook.applescript <target-workbook> <template-workbook> <template-sheet-name> [formula-map-tsv]"
    end if

    set targetWorkbookPath to item 1 of argv
    set templateWorkbookPath to item 2 of argv
    set templateSheetName to item 3 of argv
    set formulaMapPath to ""
    if (count of argv) > 3 then
        set formulaMapPath to item 4 of argv
    end if

    set targetWorkbookFile to POSIX file targetWorkbookPath as alias
    set templateWorkbookFile to POSIX file templateWorkbookPath as alias
    set targetWorkbookName to do shell script "/usr/bin/basename " & quoted form of targetWorkbookPath
    set templateWorkbookName to do shell script "/usr/bin/basename " & quoted form of templateWorkbookPath
    set wb to missing value
    set wb2 to missing value

    tell application "Microsoft Excel"
        set oldDisplayAlerts to display alerts
        set oldAskToUpdateLinks to ask to update links
        set oldAutomationSecurity to automation security

        try
            set display alerts to false
            set ask to update links to false
            set automation security to msoAutomationSecurityForceDisable

            set wb to open workbook workbook file name (targetWorkbookFile as text) update links do not update links read only false
            set wb2 to open workbook workbook file name (templateWorkbookFile as text) update links do not update links read only true

            set sourceWorksheet to worksheet templateSheetName of wb2
            set lastTargetWorksheet to worksheet (count of worksheets of wb) of wb
            copy worksheet sourceWorksheet after lastTargetWorksheet
            set copiedWorksheet to worksheet templateSheetName of wb

            if formulaMapPath is not "" then
                my applyFormulaMap(copiedWorksheet, formulaMapPath)
            end if

            close wb2 saving no
            set wb2 to missing value

            save wb
            close wb saving yes
            set wb to missing value

            set display alerts to oldDisplayAlerts
            set ask to update links to oldAskToUpdateLinks
            set automation security to oldAutomationSecurity

            return "copied"
        on error errMsg number errNum
            try
                if exists workbook templateWorkbookName then close workbook templateWorkbookName saving no
            end try
            try
                if exists workbook targetWorkbookName then close workbook targetWorkbookName saving no
            end try
            set display alerts to oldDisplayAlerts
            set ask to update links to oldAskToUpdateLinks
            set automation security to oldAutomationSecurity
            error errMsg number errNum
        end try
    end tell
end run

on applyFormulaMap(copiedWorksheet, formulaMapPath)
    set oldDelimiters to AppleScript's text item delimiters
    try
        set formulaMapFile to POSIX file formulaMapPath
        set formulaLines to paragraphs of (read formulaMapFile as «class utf8»)
        repeat with formulaLine in formulaLines
            set lineText to formulaLine as text
            if lineText is not "" then
                set AppleScript's text item delimiters to character id 9
                set formulaParts to text items of lineText
                set AppleScript's text item delimiters to oldDelimiters
                if (count of formulaParts) >= 2 then
                    set cellReference to item 1 of formulaParts
                    set formulaText to item 2 of formulaParts
                    tell application "Microsoft Excel"
                        set formula of range cellReference of copiedWorksheet to formulaText
                    end tell
                end if
            end if
        end repeat
        set AppleScript's text item delimiters to oldDelimiters
    on error errMsg number errNum
        set AppleScript's text item delimiters to oldDelimiters
        error errMsg number errNum
    end try
end applyFormulaMap
