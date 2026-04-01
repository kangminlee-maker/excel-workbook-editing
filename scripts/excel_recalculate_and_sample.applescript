on run argv
    if (count of argv) < 2 then
        error "Usage: osascript excel_recalculate_and_sample.applescript <workbook-path> <worksheet-index> [cell-ref ...]"
    end if

    set workbookPath to item 1 of argv
    set worksheetIndex to (item 2 of argv) as integer

    if (count of argv) > 2 then
        set cellRefs to items 3 thru -1 of argv
    else
        set cellRefs to {"A1"}
    end if

    tell application "Microsoft Excel"
        set wb to open workbook workbook file name workbookPath read only true
        calculate full
        set ws to worksheet worksheetIndex of wb
        set outputLines to {}

        repeat with cellRef in cellRefs
            set refText to contents of cellRef
            set cellValue to value of range refText of ws
            set end of outputLines to refText & "=" & my value_to_text(cellValue)
        end repeat

        close wb saving no
    end tell

    return my join_lines(outputLines)
end run

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
