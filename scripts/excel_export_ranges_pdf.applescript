on run argv
    if (count of argv) < 2 then
        error "Usage: osascript excel_export_ranges_pdf.applescript <workbook-path> <targets-tsv>"
    end if

    set workbookPath to item 1 of argv
    set targetsPath to item 2 of argv
    set targetsText to read (POSIX file targetsPath) as «class utf8»
    set targetLines to paragraphs of targetsText
    set workbookFile to POSIX file workbookPath as alias
    set tabChar to ASCII character 9

    tell application "Microsoft Excel"
        set oldDisplayAlerts to display alerts
        set oldAskToUpdateLinks to ask to update links
        set oldAutomationSecurity to automation security
        set wb to missing value
        set outputLines to {}

        try
            set display alerts to false
            set ask to update links to false
            set automation security to msoAutomationSecurityForceDisable

            set wb to open workbook workbook file name (workbookFile as text) update links do not update links read only true

            repeat with targetLine in targetLines
                set lineText to contents of targetLine
                if lineText is not "" then
                    set parts to my split_text(lineText, tabChar)
                    if (count of parts) is less than 4 then
                        set end of outputLines to lineText & tabChar & "error" & tabChar & "invalid target line"
                    else
                        set targetId to item 1 of parts
                        set sheetName to item 2 of parts
                        set rangeText to item 3 of parts
                        set pdfPath to item 4 of parts

                        try
                            set ws to worksheet sheetName of wb
                            set ps to page setup object of ws
                            set print area of ps to rangeText
                            set page orientation of ps to landscape
                            set print gridlines of ps to true
                            set print headings of ps to false
                            set left margin of ps to 12
                            set right margin of ps to 12
                            set top margin of ps to 12
                            set bottom margin of ps to 12
                            try
                                set zoom of ps to false
                                set fit to pages wide of ps to 1
                                set fit to pages tall of ps to 1
                            end try
                            save as ws filename ((POSIX file pdfPath) as text) file format PDF file format
                            set end of outputLines to targetId & tabChar & "captured" & tabChar & pdfPath
                        on error itemErrMsg number itemErrNum
                            set end of outputLines to targetId & tabChar & "error" & tabChar & itemErrMsg
                        end try
                    end if
                end if
            end repeat

            close wb saving no
            set wb to missing value

            set display alerts to oldDisplayAlerts
            set ask to update links to oldAskToUpdateLinks
            set automation security to oldAutomationSecurity

            return my join_lines(outputLines)
        on error errMsg number errNum
            try
                if wb is not missing value then close wb saving no
            end try
            set display alerts to oldDisplayAlerts
            set ask to update links to oldAskToUpdateLinks
            set automation security to oldAutomationSecurity
            error errMsg number errNum
        end try
    end tell
end run

on split_text(valueText, delimiterText)
    set oldDelimiters to AppleScript's text item delimiters
    set AppleScript's text item delimiters to delimiterText
    set parts to text items of valueText
    set AppleScript's text item delimiters to oldDelimiters
    return parts
end split_text

on join_lines(itemsList)
    set oldDelimiters to AppleScript's text item delimiters
    set AppleScript's text item delimiters to linefeed
    set joinedText to itemsList as string
    set AppleScript's text item delimiters to oldDelimiters
    return joinedText
end join_lines
