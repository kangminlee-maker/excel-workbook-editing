# AppleScript Examples

Use these examples only on macOS with Microsoft Excel installed.
Treat AppleScript as a thin control layer over Excel, not as the place to build workbook logic.

## 1. Before Running AppleScript

- Make sure the target workbook is not being edited in another Excel session or another terminal workflow.
- Tell the user not to open, save, rename, or navigate the target workbook while the automation is running.
- Prefer opening workbooks in read-only mode unless the task explicitly requires saving.
- Sample only the cells you need.
- Do not depend on active-sheet browsing or broad workbook scans when an explicit list of target cells will do.
- If Excel is unavailable, do not claim the workbook has been validated.
- Prefer isolated validation sessions over long-lived Excel automation flows.

## 2. Bundled Read-Only Sample

Use the bundled script when you need Excel to open a workbook, force recalculation, read a few cells, and close without saving.

Script:

- `scripts/excel_recalculate_and_sample.applescript`

Usage:

```bash
osascript skills/excel-workbook-editing/scripts/excel_recalculate_and_sample.applescript \
  "/path/to/workbook.xlsx" \
  1 \
  A1 \
  B2 \
  C10
```

Arguments:

1. workbook path
2. worksheet index
3. one or more A1-style cell references

Behavior:

- opens the workbook in read-only mode
- runs `calculate full`
- reads the requested cells
- closes without saving

Typical output:

```text
A1=Header
B2=12345
C10=<missing>
```

## 3. When To Use This Sample

- verify formula results in the real Excel engine
- compare a few key cells after regenerating a workbook in code
- inspect a suspected broken total without touching the workbook file

## 4. When Not To Use This Sample

- when another workflow is already editing the same workbook in Excel
- when you need bulk workbook edits
- when you need cross-platform automation
- when the task can be solved by patching the generator and validating manually later
- when the user is likely to click around, save, or switch sheets during the run
- when you need broad workbook scans rather than a narrow recalc-and-sample loop

## 5. Write-Back Automation Guidance

Do not start with AppleScript that opens a workbook for writing and saves changes in place.
Write-back flows are more fragile because they can conflict with:

- manual Excel sessions
- unsaved workbook state
- focus-dependent dialogs
- file locks or read-only prompts

Default pattern:

1. generate or patch in code
2. validate with the bundled read-only AppleScript or directly in Excel
3. only automate saving when the workbook is isolated and the save path is intentional

If you only need to validate calculated values, do not escalate to write-back automation.
The safest default is still:

1. patch in code
2. open in Excel
3. recalculate
4. sample a few cells
5. close without saving unless a deliberate save is part of the task

Practical rule:

- if the same issue can be diagnosed by reading 5 cells instead of 500, read 5
- if the workbook is shared or likely to be touched by a person, prefer read-only automation and manual save decisions
