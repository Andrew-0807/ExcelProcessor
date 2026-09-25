from flask import Flask, render_template, request, send_file, jsonify
import pandas as pd
import io
import os
import sys
import shutil
import tempfile
import datetime
import traceback
import zipfile

# Add processor root and module paths to sys.path first so `app.log` resolves.
_base = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_base)  # Project root

if _root not in sys.path:
    sys.path.insert(0, _root)
if _base not in sys.path:
    sys.path.insert(0, _base)

from scripts.app_info import __version__
from app.log import info as log_info, warn as log_warn, err as log_err

for _subpath in [
    os.path.join(_base, "modules", "core"),
    os.path.join(_base, "modules", "borderou"),
    os.path.join(_base, "modules", "cardcec"),
    os.path.join(_base, "modules", "tehno"),
    os.path.join(_base, "modules", "returo"),
]:
    if _subpath not in sys.path:
        sys.path.insert(0, _subpath)

# Import module modules — each in its own try/except so one failure doesn't kill the rest
try:
    from app.modules.core.valoare_sgr import SGRValueProcessor
except Exception as e:
    log_err(f"import failed:SGRValueProcessor: {e}")

try:
    from app.modules.core.format_add_column import FormatAddColumn
except Exception as e:
    log_err(f"import failed:FormatAddColumn: {e}")

try:
    from app.modules.core.excel_data_extractor import ExcelDataExtractor
except Exception as e:
    log_err(f"import failed:ExcelDataExtractor: {e}")

try:
    from app.modules.core.receptii_extractor import ReceptiiExtractor
except Exception as e:
    log_err(f"import failed:ReceptiiExtractor: {e}")

try:
    from app.modules.borderou.main import BorderouPipeline
except Exception as e:
    log_err(f"import failed:BorderouPipeline: {e}")

try:
    from app.modules.cardcec.pos_processor_fixed import (
        process_pos_file,
        detect_pos_type,
    )
except Exception as e:
    log_err(f"import failed:CardCec modules: {e}")

try:
    from app.modules.tehno.main import process_tehno
except Exception as e:
    log_err(f"import failed:process_tehno: {e}")

try:
    from app.modules.avize.main import process_avize
except Exception as e:
    log_err(f"import failed:process_avize: {e}")

try:
    from app.modules.adaos_avize.main import process_adaos_avize
except Exception as e:
    log_err(f"import failed:process_adaos_avize: {e}")

try:
    from app.modules.casa_de_marcat.main import process_casa_de_marcat
except Exception as e:
    log_err(f"import failed:process_casa_de_marcat: {e}")

try:
    from app.modules.returo.main import process_returo
except Exception as e:
    log_err(f"import failed:process_returo: {e}")

# templates/ and static/ live beside this file, frozen or not: the app ships as
# loose source next to the exe rather than inside the PyInstaller archive.
base_path = _base

# Initialize Flask with correct paths
app = Flask(
    __name__,
    template_folder=os.path.join(base_path, "templates"),
    static_folder=os.path.join(base_path, "static"),
)



def _resolve_error_base() -> str:
    """Directory under which the ``errors/`` tree is written.

    Prefers the executable dir (frozen build) or the project root, but falls
    back to the system temp dir when that location is not writable. Shared by
    the processing error dump and the user problem-report route so both land
    in the same place.
    """
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = _root

    # Verify the base directory is writable; fall back to tempdir
    probe = os.path.join(base, ".write_probe")
    try:
        with open(probe, "w") as _f:
            _f.write("")
        os.remove(probe)
    except OSError:
        fallback = tempfile.gettempdir()
        log_info(f"{base!r} not writable, using {fallback!r}")
        base = fallback
    return base


@app.route("/")
def index():
    return render_template("index.html", app_version=__version__)


@app.route("/report-problem", methods=["POST"])
def report_problem():
    """Save a user-submitted problem report (description + optional files) to
    ``errors/report/`` alongside a ``.txt`` note, mirroring the automatic error
    dump so both kinds of report live in the same place for later review."""
    description = (request.form.get("description") or "").strip()
    process_type = (request.form.get("process_type") or "").strip()
    files = request.files.getlist("file")
    has_file = any(f and f.filename for f in files)

    if not description and not has_file:
        return jsonify(
            {
                "status": "error",
                "message": "Adaugă o descriere a problemei sau atașează un fișier.",
            }
        ), 400

    try:
        report_dir = os.path.join(_resolve_error_base(), "errors", "report")
        os.makedirs(report_dir, exist_ok=True)

        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        saved_names: list[str] = []
        for file in files:
            if not file or not file.filename:
                continue
            safe_name = os.path.basename(file.filename)
            dest_path = os.path.join(report_dir, f"{ts}_{safe_name}")
            file.seek(0)
            with open(dest_path, "wb") as fout:
                fout.write(file.read())
            saved_names.append(safe_name)

        txt_path = os.path.join(report_dir, f"{ts}_report.txt")
        with open(txt_path, "w", encoding="utf-8") as ftxt:
            ftxt.write("--- User problem report ---\n")
            ftxt.write(f"Time:    {datetime.datetime.now().isoformat()}\n")
            if process_type:
                ftxt.write(f"Module:  {process_type}\n")
            if saved_names:
                ftxt.write(f"Files:   {', '.join(saved_names)}\n")
            ftxt.write("\nDescription:\n")
            ftxt.write(description or "(fără descriere)")
            ftxt.write("\n")

        log_info(f"problem report saved: {report_dir}")
        return jsonify(
            {
                "status": "ok",
                "message": "Raportul a fost salvat. Mulțumim!",
            }
        ), 200
    except Exception as e:
        log_err(f"could not save problem report: {e}")
        return jsonify(
            {
                "status": "error",
                "message": f"Nu am putut salva raportul: {e}",
            }
        ), 500


@app.route("/process", methods=["POST"])
def process_file():
    files = request.files.getlist("file")  # Get all uploaded files
    process_type = request.form["process_type"]
    # Optional starting 'Nr. inreg.' for cardcec (increments +1 per output row).
    try:
        cardcec_start_nr = int(request.form.get("start_nr", "").strip())
    except (ValueError, AttributeError):
        cardcec_start_nr = None

    try:
        outputs: list[io.BytesIO] = []
        filenames: list[str] = []
        errors: list[str] = []
        for file in files:
            # Check if the file has a valid extension
            if not (file.filename.lower().endswith(('.xlsx', '.xls', '.csv', '.pdf'))):
                log_info(f"skip (bad type): {file.filename}")
                continue
            # Check if the file is not empty
            file.seek(0, io.SEEK_END)
            file_length = file.tell()
            file.seek(0)
            if file_length == 0:
                log_info(f"skip (empty): {file.filename}")
                continue

            try:
                # Only read as Excel initially if it's NOT borderou/cardcec/furnizori
                # because those handle reading internally and may accept PDFs
                df = None
                _is_pdf = file.filename.lower().endswith(".pdf")
                if _is_pdf and process_type not in {
                    "borderou",
                    "cardcec",
                    "furnizori",
                    "adaos",
                    "sgr",
                    "sales_transform",
                    "returo",
                }:
                    raise ValueError(
                        f"Process type '{process_type}' does not support PDF files."
                    )
                if not _is_pdf and process_type not in {"borderou", "cardcec", "sgr", "returo"}:
                    _excel_engine = "xlrd" if file.filename.lower().endswith(".xls") else "openpyxl"
                    df = pd.read_excel(file, engine=_excel_engine)
                # PDF handling for generic modules (adaos, sales_transform).
                # SGR PDFs are text-only (no tables) so they are handled separately
                # inside the process_type == "sgr" block below.
                if _is_pdf and process_type in {
                    "adaos",
                    "sales_transform",
                }:
                    from app.modules.core.pdf_extractor import (
                        extract_dataframe_from_pdf,
                    )

                    temp_dir = tempfile.mkdtemp()
                    temp_file_path = os.path.join(temp_dir, file.filename)
                    try:
                        file.seek(0)
                        with open(temp_file_path, "wb") as tf:
                            tf.write(file.read())
                        df = extract_dataframe_from_pdf(temp_file_path)
                    finally:
                        shutil.rmtree(temp_dir, ignore_errors=True)

                # Process the data based on the process_type
                if process_type == "adaos":
                    processor = FormatAddColumn()
                    result_df = processor.process_dataframe(df)
                    if result_df is None:
                        raise ValueError(
                            f"Adaos processing returned no data for '{file.filename}'. "
                            "Check that the file has the required columns (e.g. '% TVA VANZARE')."
                        )
                elif process_type == "sgr":
                    # SGR accepts a RetuRO/Borderou PDF or an Excel (raw Borderou
                    # export or a pre-formatted SGR template). Both are parsed
                    # from a temp file so multi-row borderou headers survive
                    # (pd.read_excel would mangle them).
                    temp_dir = tempfile.mkdtemp()
                    temp_file_path = os.path.join(temp_dir, file.filename)
                    try:
                        file.seek(0)
                        with open(temp_file_path, "wb") as tf:
                            tf.write(file.read())
                        processor = SGRValueProcessor()
                        if _is_pdf:
                            result_df = processor.process_pdf_file(
                                temp_file_path, start_nr=cardcec_start_nr
                            )
                        else:
                            result_df = processor.process_excel_file(
                                temp_file_path, start_nr=cardcec_start_nr
                            )
                    finally:
                        shutil.rmtree(temp_dir, ignore_errors=True)
                    if result_df is None:
                        raise ValueError(
                            f"Fisierul SGR '{file.filename}' nu contine randuri de date. "
                            "Asigura-te ca ai incarcat un PDF/Excel RetuRO-SGR valid "
                            "sau un Borderou de Vanzare cu valori SGR (Netaxabil)."
                        )
                elif process_type == "returo":
                    # RetuRO voucher xlsx is multi-sheet; the module reads all
                    # sheets from a temp file (pd.read_excel would see only one).
                    temp_dir = tempfile.mkdtemp()
                    temp_file_path = os.path.join(temp_dir, file.filename)
                    try:
                        file.seek(0)
                        with open(temp_file_path, "wb") as tf:
                            tf.write(file.read())
                        result_df = process_returo(
                            temp_file_path, start_nr=cardcec_start_nr
                        )
                    finally:
                        shutil.rmtree(temp_dir, ignore_errors=True)
                    if result_df is None:
                        raise ValueError(
                            f"Fisierul RetuRO '{file.filename}' nu contine randuri "
                            "'Plata Voucher RetuRO'. Incarca exportul brut "
                            "'Garantii SGR Platite cu Numerar'."
                        )
                elif process_type == "furnizori":
                    if _is_pdf:

                        temp_dir = tempfile.mkdtemp()
                        temp_file_path = os.path.join(temp_dir, file.filename)
                        try:
                            file.seek(0)
                            with open(temp_file_path, "wb") as tf:
                                tf.write(file.read())
                            extractor = ReceptiiExtractor()
                            result_df = extractor.process(
                                temp_file_path, original_filename=file.filename
                            )
                        finally:
                            shutil.rmtree(temp_dir, ignore_errors=True)
                    else:
                        processor = ExcelDataExtractor()
                        result_df = processor.process_dataframe(df)
                elif process_type == "borderou":
                    # Handle borderou processing - save file to a temp dir using the
                    # ORIGINAL filename so that M1/M2 pattern matching works downstream.

                    temp_dir = tempfile.mkdtemp()
                    temp_file_path = os.path.join(temp_dir, file.filename)
                    try:
                        file.seek(0)
                        with open(temp_file_path, "wb") as temp_file:
                            temp_file.write(file.read())
                    except Exception:
                        shutil.rmtree(temp_dir, ignore_errors=True)
                        raise

                    try:
                        pipeline = BorderouPipeline()
                        result = pipeline.process_file(temp_file_path)

                        if result and result != "skipped":
                            # For borderou, we need to read the generated file(s)
                            if isinstance(result, list):
                                # Multiple files - we'll zip them
                                for xlsx_file in result:
                                    result_df = pd.read_excel(xlsx_file)
                                    output = io.BytesIO()
                                    result_df.to_excel(
                                        output, index=False, engine="openpyxl"
                                    )
                                    output.seek(0)
                                    outputs.append(output)
                                    filenames.append(
                                        f"borderou_{os.path.basename(xlsx_file)}"
                                    )
                                continue  # Skip the normal processing below
                            else:
                                # Single file
                                result_df = pd.read_excel(result)
                        else:
                            log_warn(f"borderou produced no output: {file.filename}")
                            continue
                    finally:
                        # Clean up entire temp directory
                        shutil.rmtree(temp_dir, ignore_errors=True)
                elif process_type == "cardcec":
                    # Save the uploaded file temporarily with unique name
                    original_ext = os.path.splitext(file.filename)[1]
                    if not original_ext:
                        original_ext = ".xlsx"
                    fd, temp_file_path = tempfile.mkstemp(suffix=original_ext)
                    fd_closed = False
                    try:
                        with os.fdopen(fd, "wb") as temp_file:
                            fd_closed = True  # os.fdopen takes ownership of fd
                            file.seek(0)
                            temp_file.write(file.read())
                    except Exception:
                        if not fd_closed:
                            os.close(fd)
                        if os.path.exists(temp_file_path):
                            os.remove(temp_file_path)
                        raise

                    try:
                        # Process straight to a DataFrame (no CSV round-trip); the
                        # shared output path below turns it into the xlsx download.
                        pos_type = detect_pos_type(file.filename)
                        result_df = process_pos_file(
                            temp_file_path,
                            output_path=None,
                            pos_type=pos_type,
                            original_filename=file.filename,
                            start_nr=cardcec_start_nr,
                        )
                    except Exception:
                        # surfaced cleanly by the outer handler below
                        raise
                    finally:
                        # Clean up the temp input file
                        if os.path.exists(temp_file_path):
                            os.remove(temp_file_path)
                elif process_type == "tehno":
                    result_df = process_tehno(df)
                elif process_type == "avize":
                    result_df = process_avize(df, file.filename)
                elif process_type == "adaos_avize":
                    result_df = process_adaos_avize(df, file.filename)
                elif process_type == "casa_de_marcat":
                    result_df = process_casa_de_marcat(df)
                else:
                    return "Invalid process type", 400

                # Save the processed DataFrame to a BytesIO object
                output = io.BytesIO()
                result_df.to_excel(output, index=False, engine="openpyxl")
                output.seek(0)
                outputs.append(output)
                # Save the filename for the zip. Output is always openpyxl xlsx,
                # so force the .xlsx extension regardless of the input ext
                # (a .xls/.pdf name over xlsx bytes triggers Excel's
                # "format and extension don't match" warning).
                base_name, _ = os.path.splitext(os.path.basename(file.filename))
                processed_filename = f"{process_type} - {base_name}.xlsx"
                filenames.append(processed_filename)
            except Exception as e:
                # Full traceback goes to the error .txt dump below; console stays terse.
                tb = traceback.format_exc()
                errors.append({"file": file.filename, "error": str(e), "traceback": tb})

                # Save the failed file + a text report to errors/<module>/
                try:
                    err_dir = os.path.join(_resolve_error_base(), "errors", process_type)
                    os.makedirs(err_dir, exist_ok=True)

                    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    safe_name = os.path.basename(file.filename)
                    err_file_path = os.path.join(err_dir, f"{ts}_{safe_name}")
                    err_txt_path = os.path.join(err_dir, f"{ts}_{safe_name}.txt")

                    file.seek(0)
                    with open(err_file_path, "wb") as fout:
                        fout.write(file.read())
                    with open(err_txt_path, "w", encoding="utf-8") as ftxt:
                        ftxt.write(f"File:   {file.filename}\n")
                        ftxt.write(f"Module: {process_type}\n")
                        ftxt.write(f"Time:   {datetime.datetime.now().isoformat()}\n")
                        ftxt.write(f"Error:  {e}\n\n")
                        ftxt.write("--- Traceback ---\n")
                        ftxt.write(tb)
                    log_err(f"{process_type}: {file.filename} - {e}", where=err_dir)
                except Exception as dump_err:
                    log_err(f"{process_type}: {file.filename} - {e}")
                    log_warn(f"(could not save error dump: {dump_err})")

                continue

        # These lines should be OUTSIDE the for loop!
        if not outputs:
            if errors:
                # Return JSON with full debug info so JS console can show it
                from flask import jsonify

                return jsonify(
                    {
                        "status": "error",
                        "message": f"Processing failed for {len(errors)} file(s)",
                        "errors": errors,
                    }
                ), 500
            return "No valid files were provided for processing.", 400

        response_obj = None
        # If some files succeeded but others failed, include warnings as a header
        if len(outputs) == 1:
            response_obj = send_file(
                outputs[0], download_name=filenames[0], as_attachment=True
            )
        else:
            # If multiple files, zip them
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zipf:
                for output, fname in zip(outputs, filenames):
                    output.seek(0)
                    zipf.writestr(fname, output.read())
            zip_buffer.seek(0)
            response_obj = send_file(
                zip_buffer,
                download_name="processed_files.zip",
                as_attachment=True,
                mimetype="application/zip",
            )

        # Attach error warnings as a header so JS can log them to console
        if errors:
            import json

            error_summary = json.dumps(
                [{"file": e["file"], "error": e["error"]} for e in errors]
            )
            response_obj.headers["X-Processing-Warnings"] = error_summary

        return response_obj

    except Exception as e:
        log_err(f"request failed: {e}")
        if app.debug:
            traceback.print_exc()
        return f"An error occurred: {str(e)}", 500


def run_app(host: str = "127.0.0.1", port: int = 5000, debug: bool = False) -> None:
    """Helper so other modules can host the Flask app."""
    app.run(debug=debug, host=host, port=port)


if __name__ == "__main__":
    run_app()
