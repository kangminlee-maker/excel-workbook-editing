on run argv
    if (count of argv) < 2 then
        error "Usage: osascript excel_recalculate_and_sample.applescript <workbook-path> <worksheet-index-or-name> [cell-ref ...]"
    end if

    set workbookPath to item 1 of argv
    set worksheetRef to item 2 of argv

    if (count of argv) > 2 then
        set cellRefs to items 3 thru -1 of argv
    else
        set cellRefs to {"A1"}
    end if

    set workbookFile to POSIX file workbookPath as alias

    tell application "Microsoft Excel"
        set oldDisplayAlerts to display alerts
        set oldAskToUpdateLinks to ask to update links
        set oldAutomationSecurity to automation security
        set wb to missing value

        try
            set display alerts to false
            set ask to update links to false
            set automation security to msoAutomationSecurityForceDisable

            set wb to open workbook workbook file name (workbookFile as text) update links do not update links read only true
            calculate full rebuild

            if my is_integer_text(worksheetRef) then
                set ws to worksheet (worksheetRef as integer) of wb
            else
                set ws to worksheet worksheetRef of wb
            end if

            set outputLines to {}
            repeat with cellRef in cellRefs
                set refText to contents of cellRef
                set cellValue to value of range refText of ws
                set end of outputLines to refText & "=" & my value_to_text(cellValue)
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

on is_integer_text(v)
    try
        set _n to v as integer
        return true
    on error
        return false
    end try
end is_integer_text

on value_to_text(v)
    if v is missing value then
        return "<missing>"
    end if

    return v as string
end value_to_text

on join_lines(itemsList)
    set oldDelimiters to AppleScript's text item delimiters
    set AppleScript's text item delimiters to linefeed
    set joinedText to itemsList as string
    set AppleScript's text item delimiters to oldDelimiters
    return joinedText
end join_lines
