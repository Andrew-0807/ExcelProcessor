"""
cli.py — Developer CLI for MomAutomations
==========================================

Invoke any processing module directly from the command line without
starting the Flask server.

Usage:
    python -m app.cli --type borderou --input file.xlsx --output out.xlsx
    python -m app.cli --type borderou --schema
    python -m app.cli --type cardcec --input file.xlsx --output out.xlsx --verbose

Process types: borderou, cardcec, sales_transform, extract, minus, sgr, adaos
"""

import argparse
import os
import sys
import tempfile
import traceback

from rich.console import Console
from rich.table import Table
from rich import traceback as rich_traceback

_console = Console()
_err = Console(stderr=True)

# ── sys.path setup (mirrored from server.py) ────────────────────────────────

_base = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_base)

for _p in [_root, _base]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

for _subpath in [
    os.path.join(_base, "modules", "core"),
    os.path.join(_base, "modules", "borderou"),
    os.path.join(_base, "modules", "cardcec"),
    os.path.join(_base, "modules", "sales_transform"),
]:
    if _subpath not in sys.path:
        sys.path.insert(0, _subpath)

# ── Module imports (isolated try/except so one failure doesn't block others) ─

_import_errors: dict[str, str] = {}

SGRValueProcessor = None
try:
    from app.modules.core.valoare_sgr import SGRValueProcessor
except Exception as e:
    _import_errors["sgr"] = str(e)

ValoareMinus = None
try:
    from app.modules.core.valoare_minus import ValoareMinus
except Exception as e:
    _import_errors["minus"] = str(e)

FormatAddColumn = None
try:
    from app.modules.core.format_add_column import FormatAddColumn
except Exception as e:
    _import_errors["adaos"] = str(e)

ExcelDataExtractor = None
try:
    from app.modules.core.excel_data_extractor import ExcelDataExtractor
except Exception as e:
    _import_errors["furnizori"] = str(e)

BorderouPipeline = None
try:
    from app.modules.borderou.main import BorderouPipeline
    from app.modules.borderou.main import OUTPUT_COLUMNS as BORDEROU_COLUMNS
except Exception as e:
    _import_errors["borderou"] = str(e)
    BORDEROU_COLUMNS = None

process_pos_file = None
detect_pos_type = None
CARDCEC_COLUMNS = None
try:
    from app.modules.cardcec.pos_processor_fixed import (
        process_pos_file,
        detect_pos_type,
    )
    from app.modules.cardcec.pos_processor_fixed import OUTPUT_COLUMNS as CARDCEC_COLUMNS
except Exception as e:
    _import_errors["cardcec"] = str(e)

SalesTransformProcessor = None
try:
    from app.modules.sales_transform.sales_transform import SalesTransformProcessor
except Exception as e:
    _import_errors["sales_transform"] = str(e)

PROCESS_TYPES = ["borderou", "cardcec", "sales_transform", "furnizori", "minus", "sgr", "adaos"]


# ── Schema registry ──────────────────────────────────────────────────────────

def get_schema(process_type: str):
    """Return OUTPUT_COLUMNS list for a process type, or None if not fixed."""
    if process_type == "borderou":
        return BORDEROU_COLUMNS
    if process_type == "cardcec":
        return CARDCEC_COLUMNS
    return None


# ── Processing dispatch ──────────────────────────────────────────────────────

def _process(process_type: str, input_path: str, output_path: str, verbose: bool) -> None:
    """Run a module on input_path and write result to output_path."""
    import pandas as pd
    import shutil

    if verbose:
        _err.print(f"[dim]▶ processing[/dim] [cyan]{process_type}[/cyan] [dim]←[/dim] [blue]{input_path}[/blue]")

    if process_type == "borderou":
        if BorderouPipeline is None:
            raise RuntimeError(f"borderou module failed to import: {_import_errors.get('borderou')}")

        temp_dir = tempfile.mkdtemp()
        try:
            # Preserve original filename for pattern matching inside the pipeline
            orig_name = os.path.basename(input_path)
            temp_input = os.path.join(temp_dir, orig_name)
            shutil.copy2(input_path, temp_input)

            pipeline = BorderouPipeline()
            result = pipeline.process_file(temp_input)

            if not result or result == "skipped":
                raise RuntimeError("borderou pipeline returned no result (file may be unsupported type)")

            # Result may be a list of output paths or a single path
            if isinstance(result, list):
                result_path = result[0]
                if verbose and len(result) > 1:
                    _err.print(f"[yellow]⚠[/yellow] borderou produced [bold]{len(result)}[/bold] files; writing first to output")
            else:
                result_path = result

            result_df = pd.read_excel(result_path)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    elif process_type == "cardcec":
        if process_pos_file is None:
            raise RuntimeError(f"cardcec module failed to import: {_import_errors.get('cardcec')}")

        fd, temp_input = tempfile.mkstemp(suffix=".xlsx")
        temp_csv = None
        try:
            with os.fdopen(fd, "wb") as f:
                with open(input_path, "rb") as src:
                    f.write(src.read())

            csv_dir = tempfile.mkdtemp()
            temp_csv = os.path.join(csv_dir, os.path.splitext(os.path.basename(input_path))[0] + ".csv")

            pos_type = detect_pos_type(os.path.basename(input_path))
            process_pos_file(temp_input, temp_csv, pos_type)

            result_df = pd.read_csv(temp_csv, encoding="utf-8-sig")
        finally:
            if os.path.exists(temp_input):
                os.remove(temp_input)
            if temp_csv and os.path.exists(temp_csv):
                os.remove(temp_csv)

    else:
        # In-memory DataFrame modules
        df = pd.read_excel(input_path, engine="openpyxl")
        df.name = os.path.basename(input_path)

        if process_type == "sales_transform":
            if SalesTransformProcessor is None:
                raise RuntimeError(f"sales_transform module failed to import: {_import_errors.get('sales_transform')}")
            processor = SalesTransformProcessor()
            result_df = processor.process_dataframe(df)

        elif process_type == "furnizori":
            if ExcelDataExtractor is None:
                raise RuntimeError(f"furnizori module failed to import: {_import_errors.get('furnizori')}")
            processor = ExcelDataExtractor()
            result_df = processor.process_dataframe(df)

        elif process_type == "minus":
            if ValoareMinus is None:
                raise RuntimeError(f"minus module failed to import: {_import_errors.get('minus')}")
            processor = ValoareMinus()
            result_df = processor.process_dataframe(df)

        elif process_type == "sgr":
            if SGRValueProcessor is None:
                raise RuntimeError(f"sgr module failed to import: {_import_errors.get('sgr')}")
            processor = SGRValueProcessor()
            result_df = processor.process_dataframe(df)

        elif process_type == "adaos":
            if FormatAddColumn is None:
                raise RuntimeError(f"adaos module failed to import: {_import_errors.get('adaos')}")
            processor = FormatAddColumn()
            result_df = processor.process_dataframe(df)

        else:
            raise ValueError(f"Unknown process type: {process_type}")

    if verbose:
        _err.print(f"[dim]✎ writing →[/dim] [blue]{output_path}[/blue]")

    result_df.to_excel(output_path, index=False, engine="openpyxl")


# ── Argument parsing ─────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli",
        description="MomAutomations developer CLI — run any processing module from the terminal.",
    )
    parser.add_argument(
        "--type", "-t",
        dest="process_type",
        required=True,
        choices=PROCESS_TYPES,
        metavar="TYPE",
        help=f"Processing module to run. One of: {', '.join(PROCESS_TYPES)}",
    )
    parser.add_argument(
        "--input", "-i",
        dest="input",
        nargs="+",
        metavar="FILE",
        help="Input Excel file(s) to process.",
    )
    parser.add_argument(
        "--output", "-o",
        dest="output",
        metavar="FILE",
        help="Output .xlsx file path.",
    )
    parser.add_argument(
        "--schema", "-s",
        action="store_true",
        help="Print the OUTPUT_COLUMNS schema for the selected type and exit.",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print debug information to stderr during processing.",
    )
    return parser


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # ── Verbose: report import status ───────────────────────────────────────
    if args.verbose:
        for ptype in PROCESS_TYPES:
            if ptype in _import_errors:
                _err.print(f"[yellow]⚠  {ptype:<16}[/yellow] [dim]{_import_errors[ptype]}[/dim]")
            else:
                _err.print(f"[green]✓  {ptype}[/green]")

    # ── Schema mode ─────────────────────────────────────────────────────────
    if args.schema:
        cols = get_schema(args.process_type)
        if cols is None:
            _console.print(f"[yellow]Module [bold]{args.process_type}[/bold] has no fixed OUTPUT_COLUMNS schema.[/yellow]")
        else:
            table = Table(title=f"[bold]{args.process_type}[/bold] schema ({len(cols)} columns)", show_header=True, header_style="bold magenta")
            table.add_column("#", style="dim", width=4)
            table.add_column("Column name", style="cyan")
            for i, col in enumerate(cols, 1):
                table.add_row(str(i), col)
            _console.print(table)
        sys.exit(0)

    # ── Normal mode: enforce --input and --output ────────────────────────────
    if not args.input:
        parser.error("--input is required when not using --schema")
    if not args.output:
        parser.error("--output is required when not using --schema")

    # Validate output parent directory
    out_parent = os.path.dirname(os.path.abspath(args.output))
    if not os.path.isdir(out_parent):
        _err.print(f"[bold red]Error:[/bold red] output directory does not exist: [blue]{out_parent}[/blue]")
        sys.exit(1)

    # Process each input file (last one wins if multiple and single output)
    for input_path in args.input:
        if not os.path.isfile(input_path):
            _err.print(f"[bold red]Error:[/bold red] input file not found: [blue]{input_path}[/blue]")
            sys.exit(1)

        try:
            _process(args.process_type, input_path, args.output, args.verbose)
        except Exception as exc:
            _err.print(f"[bold red]Error:[/bold red] {exc}")
            if args.verbose:
                rich_traceback.install()
                traceback.print_exc(file=sys.stderr)
            sys.exit(1)

    if args.verbose:
        _err.print(f"[bold green]✓ done[/bold green] → [blue]{args.output}[/blue]")


if __name__ == "__main__":
    main()
