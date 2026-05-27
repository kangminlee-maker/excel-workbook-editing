from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path

APPLESCRIPT_PATH = Path(__file__).with_name("excel_recalculate_and_sample.applescript")
POWERSHELL_PATH = Path(__file__).with_name("excel_recalculate_and_sample.ps1")
MAC_EXCEL_CONTAINER_DOCUMENTS = (
    Path.home() / "Library/Containers/com.microsoft.Excel/Data/Documents"
)
DEFAULT_SANDBOX_SUBDIR = "excel_workbook_editing_validation"


class ExcelEngineError(RuntimeError):
    """Raised when real Excel-engine validation cannot complete."""


def sample_workbook_cells(
    workbook_path: Path,
    worksheet: int | str,
    cell_refs: list[str],
    *,
    timeout: int = 180,
    sandbox_copy: bool = True,
    sandbox_subdir: str = DEFAULT_SANDBOX_SUBDIR,
) -> dict[str, str]:
    """Recalculate a workbook in Microsoft Excel and return selected cell values.

    By default this opens a temporary workbook copy before driving desktop Excel.
    On macOS it uses AppleScript. On Windows it uses PowerShell and Excel COM
    Automation. Both paths keep validation on the real Excel engine while
    avoiding locks on the source workbook.
    """
    if not cell_refs:
        raise ValueError("cell_refs must not be empty")
    _ensure_platform_helper()

    workbook_path = workbook_path.expanduser().resolve()
    if not workbook_path.exists():
        raise FileNotFoundError(f"missing workbook: {workbook_path}")

    if sandbox_copy:
        sandbox_root = _excel_sandbox_root(sandbox_subdir)
        sandbox_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="run_", dir=str(sandbox_root)) as tmp_dir:
            tmp_path = Path(tmp_dir) / workbook_path.name
            shutil.copy2(workbook_path, tmp_path)
            output = _run_excel_engine(tmp_path, worksheet, cell_refs, timeout)
    else:
        output = _run_excel_engine(workbook_path, worksheet, cell_refs, timeout)

    return _parse_cell_output(output)


def _ensure_platform_helper() -> None:
    system = platform.system()
    if system == "Darwin":
        if not APPLESCRIPT_PATH.exists():
            raise FileNotFoundError(f"missing AppleScript helper: {APPLESCRIPT_PATH}")
        return
    if system == "Windows":
        if not POWERSHELL_PATH.exists():
            raise FileNotFoundError(f"missing PowerShell helper: {POWERSHELL_PATH}")
        return
    raise ExcelEngineError(
        "Real Microsoft Excel-engine validation is supported only on macOS "
        "or Windows desktop environments. Use structural checks only, and "
        "report Excel-engine validation as incomplete."
    )


def _excel_sandbox_root(sandbox_subdir: str) -> Path:
    override = os.environ.get("EXCEL_ENGINE_SAMPLE_SANDBOX_DIR")
    if override:
        return Path(override).expanduser().resolve()
    if platform.system() == "Darwin":
        if MAC_EXCEL_CONTAINER_DOCUMENTS.exists():
            return MAC_EXCEL_CONTAINER_DOCUMENTS / sandbox_subdir
        raise ExcelEngineError(
            "Microsoft Excel sandbox container not found. "
            "Open Microsoft Excel once, then rerun Excel-engine validation."
        )
    return Path(tempfile.gettempdir()) / sandbox_subdir


def _run_excel_engine(
    workbook_path: Path,
    worksheet: int | str,
    cell_refs: list[str],
    timeout: int,
) -> str:
    system = platform.system()
    if system == "Darwin":
        return _run_applescript(workbook_path, worksheet, cell_refs, timeout)
    if system == "Windows":
        return _run_powershell(workbook_path, worksheet, cell_refs, timeout)
    raise ExcelEngineError(f"unsupported desktop Excel automation platform: {system}")


def _run_applescript(
    workbook_path: Path,
    worksheet: int | str,
    cell_refs: list[str],
    timeout: int,
) -> str:
    cmd = [
        "/usr/bin/osascript",
        str(APPLESCRIPT_PATH),
        str(workbook_path),
        str(worksheet),
        *cell_refs,
    ]
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise ExcelEngineError(
            "Excel-engine validation timed out. Close modal Excel dialogs and retry."
        ) from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        raise ExcelEngineError(f"Excel-engine validation failed: {detail}") from exc
    return result.stdout.strip()


def _run_powershell(
    workbook_path: Path,
    worksheet: int | str,
    cell_refs: list[str],
    timeout: int,
) -> str:
    powershell = shutil.which("pwsh") or shutil.which("powershell.exe")
    if not powershell:
        raise ExcelEngineError(
            "PowerShell executable not found. Install PowerShell or run from a "
            "Windows desktop environment with Windows PowerShell available."
        )

    cmd = [
        powershell,
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(POWERSHELL_PATH),
        "-Workbook",
        str(workbook_path),
        "-Worksheet",
        str(worksheet),
        "-Cells",
        *cell_refs,
    ]
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise ExcelEngineError(
            "Excel-engine validation timed out. Close modal Excel dialogs and retry."
        ) from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        raise ExcelEngineError(f"Excel-engine validation failed: {detail}") from exc
    return result.stdout.strip()


def _parse_cell_output(output: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in output.splitlines():
        if not line.strip():
            continue
        cell, raw = line.split("=", 1)
        values[cell] = raw
    return values


def _worksheet_arg(value: str) -> int | str:
    try:
        return int(value)
    except ValueError:
        return value


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Recalculate an xlsx in the real Microsoft Excel engine and sample cells."
    )
    parser.add_argument("workbook", type=Path)
    parser.add_argument("worksheet", type=_worksheet_arg)
    parser.add_argument("cells", nargs="+")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument(
        "--direct",
        action="store_true",
        help="Open the source workbook path directly instead of a temporary copy.",
    )
    args = parser.parse_args()

    values = sample_workbook_cells(
        args.workbook,
        args.worksheet,
        args.cells,
        timeout=args.timeout,
        sandbox_copy=not args.direct,
    )
    for cell in args.cells:
        print(f"{cell}={values[cell]}")


if __name__ == "__main__":
    main()
