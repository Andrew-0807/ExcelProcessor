from flask import Flask, render_template, request, send_file
import pandas as pd
import io
import os
import sys
import tempfile
import datetime
import traceback
import zipfile

# Add processor root and module paths to sys.path
_base = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_base)  # Project root

if _root not in sys.path:
    sys.path.insert(0, _root)
if _base not in sys.path:
    sys.path.insert(0, _base)

from scripts.app_info import __version__

for _subpath in [
    os.path.join(_base, "modules", "core"),
    os.path.join(_base, "modules", "borderou"),
    os.path.join(_base, "modules", "cardcec"),
    os.path.join(_base, "modules", "sales_transform"),
]:
    if _subpath not in sys.path:
        sys.path.insert(0, _subpath)

# Import module modules — each in its own try/except so one failure doesn't kill the rest
try:
    from app.modules.core.valoare_sgr import SGRValueProcessor
except Exception as e:
    print(f"Error importing SGRValueProcessor: {e}")

try:
    from app.modules.core.valoare_minus import ValoareMinus
except Exception as e:
    print(f"Error importing ValoareMinus: {e}")

try:
    from app.modules.core.format_add_column import FormatAddColumn
except Exception as e:
    print(f"Error importing FormatAddColumn: {e}")

try:
    from app.modules.core.excel_data_extractor import ExcelDataExtractor
except Exception as e:
    print(f"Error importing ExcelDataExtractor: {e}")

try:
    from app.modules.core.receptii_extractor import ReceptiiExtractor
except Exception as e:
    print(f"Error importing ReceptiiExtractor: {e}")

try:
    from app.modules.borderou.main import BorderouPipeline
except Exception as e:
    print(f"Error importing BorderouPipeline: {e}")

try:
    from app.modules.cardcec.pos_processor_fixed import (
        process_pos_file,
        detect_pos_type,
    )
except Exception as e:
    print(f"Error importing CardCec modules: {e}")

try:
    from app.modules.sales_transform.sales_transform import SalesTransformProcessor
except Exception as e:
    print(f"Error importing SalesTransformProcessor: {e}")

# Get the base path for templates and static files
# This handles both normal execution and PyInstaller frozen execution
if getattr(sys, "frozen", False):
    # Running as a PyInstaller bundle
    base_path = sys._MEIPASS
else:
    # Running normally
    base_path = os.path.dirname(os.path.abspath(__file__))

# Initialize Flask with correct paths
app = Flask(
    __name__,
    template_folder=os.path.join(base_path, "templates"),
    static_folder=os.path.join(base_path, "static"),
)


def create_app() -> Flask:
    """Expose the Flask application for external runners."""
    return app


def _valid_file(filename: str) -> bool:
    lower_name = filename.lower()
    return (
        lower_name.endswith(".xlsx")
        or lower_name.endswith(".xls")
        or lower_name.endswith(".csv")
        or lower_name.endswith(".pdf")
    )


@app.route("/")
def index():
    return render_template("index.html", app_version=__version__)


@app.route("/process", methods=["POST"])
def process_file():
    files = request.files.getlist("file")  # Get all uploaded files
    process_type = request.form["process_type"]

    try:
        outputs: list[io.BytesIO] = []
        filenames: list[str] = []
        errors: list[str] = []
        for file in files:
            # Check if the file has a valid extension
            if not _valid_file(file.filename):
                print(f"Skipping invalid file type: {file.filename}")
                continue
            # Check if the file is not empty
            file.seek(0, io.SEEK_END)
            file_length = file.tell()
            file.seek(0)
            if file_length == 0:
                print(f"Skipping empty file: {file.filename}")
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
                    "minus",
                    "sales_transform",
                }:
                    raise ValueError(
                        f"Process type '{process_type}' does not support PDF files."
                    )
                if not _is_pdf and process_type not in {"borderou", "cardcec"}:
                    _excel_engine = "xlrd" if file.filename.lower().endswith(".xls") else "openpyxl"
                    df = pd.read_excel(file, engine=_excel_engine)
                    df.name = file.filename
                # PDF handling for generic modules (adaos, minus, sales_transform).
                # SGR PDFs are text-only (no tables) so they are handled separately
                # inside the process_type == "sgr" block below.
                if _is_pdf and process_type in {
                    "adaos",
                    "minus",
                    "sales_transform",
                }:
                    import shutil as _shutil
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
                        df.name = file.filename
                    finally:
                        _shutil.rmtree(temp_dir, ignore_errors=True)

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
                    if _is_pdf:
                        import shutil as _shutil
                        temp_dir = tempfile.mkdtemp()
                        temp_file_path = os.path.join(temp_dir, file.filename)
                        try:
                            file.seek(0)
                            with open(temp_file_path, "wb") as tf:
                                tf.write(file.read())
                            processor = SGRValueProcessor()
                            result_df = processor.process_pdf_file(temp_file_path)
                        finally:
                            _shutil.rmtree(temp_dir, ignore_errors=True)
                    else:
                        processor = SGRValueProcessor()
                        result_df = processor.process_dataframe(df)
                    if result_df is None:
                        raise ValueError(
                            f"PDF-ul SGR '{file.filename}' nu contine randuri de date. "
                            "Asigura-te ca ai incarcat un PDF RetuRO-SGR valid "
                            "(Garantii SGR Platite cu Numerar)."
                        )
                elif process_type == "minus":
                    processor = ValoareMinus()
                    result_df = processor.process_dataframe(df)
                    if result_df is None:
                        raise ValueError(
                            f"Minus processing returned no data for '{file.filename}'."
                        )
                elif process_type == "furnizori":
                    if _is_pdf:
                        import shutil as _shutil

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
                            _shutil.rmtree(temp_dir, ignore_errors=True)
                    else:
                        processor = ExcelDataExtractor()
                        result_df = processor.process_dataframe(df)
                elif process_type == "borderou":
                    # Handle borderou processing - save file to a temp dir using the
                    # ORIGINAL filename so that M1/M2 pattern matching works downstream.
                    import shutil as _shutil

                    temp_dir = tempfile.mkdtemp()
                    temp_file_path = os.path.join(temp_dir, file.filename)
                    try:
                        file.seek(0)
                        with open(temp_file_path, "wb") as temp_file:
                            temp_file.write(file.read())
                    except Exception:
                        _shutil.rmtree(temp_dir, ignore_errors=True)
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
                            print(f"Borderou processing failed for {file.filename}")
                            continue
                    finally:
                        # Clean up entire temp directory
                        _shutil.rmtree(temp_dir, ignore_errors=True)
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
                        # Create CSV directory structure like the original expects
                        csv_dir = "csv"
                        if not os.path.exists(csv_dir):
                            os.makedirs(csv_dir)

                        # Create proper output path for CSV
                        filename_without_ext = os.path.splitext(file.filename)[0]
                        temp_output_path = os.path.join(
                            csv_dir, f"{filename_without_ext}.csv"
                        )

                        # Process the file with the original standalone processor
                        pos_type = detect_pos_type(file.filename)
                        process_pos_file(
                            temp_file_path,
                            temp_output_path,
                            pos_type,
                            original_filename=file.filename,
                        )

                        # Read the processed CSV file back into a DataFrame
                        result_df = pd.read_csv(temp_output_path, encoding="utf-8-sig")

                        # Clean up the temporary CSV file
                        if os.path.exists(temp_output_path):
                            os.remove(temp_output_path)
                    except Exception as e:
                        print(
                            f"Error processing {file.filename} with POS processor: {e}"
                        )
                        raise
                    finally:
                        # Clean up the temp input file
                        if os.path.exists(temp_file_path):
                            os.remove(temp_file_path)
                elif process_type == "sales_transform":
                    processor = SalesTransformProcessor()
                    result_df = processor.process_dataframe(df)
                else:
                    return "Invalid process type", 400

                # Save the processed DataFrame to a BytesIO object
                output = io.BytesIO()
                result_df.to_excel(output, index=False, engine="openpyxl")
                output.seek(0)
                outputs.append(output)
                # Save the filename for the zip
                original_filename = file.filename
                base_name, ext = os.path.splitext(original_filename)
                if ext.lower() == ".pdf":
                    original_filename = base_name + ".xlsx"
                processed_filename = f"{process_type} - {original_filename}"
                filenames.append(processed_filename)
            except Exception as e:
                # Log full traceback to server console for debugging
                tb = traceback.format_exc()
                error_msg = f"Error processing {file.filename}: {e}"
                print(f"\n{'=' * 60}")
                print(f"ERROR: {error_msg}")
                print(tb)
                print(f"{'=' * 60}\n")
                errors.append({"file": file.filename, "error": str(e), "traceback": tb})

                # Save the failed file + a text report to errors/<module>/
                try:
                    if getattr(sys, "frozen", False):
                        err_base = os.path.dirname(sys.executable)
                    else:
                        err_base = _root

                    # Verify the base directory is writable; fall back to tempdir
                    _probe = os.path.join(err_base, ".write_probe")
                    try:
                        with open(_probe, "w") as _f:
                            _f.write("")
                        os.remove(_probe)
                    except OSError:
                        import tempfile as _tempfile

                        _fallback = _tempfile.gettempdir()
                        print(
                            f"[error dump] {err_base!r} is not writable, using {_fallback!r}"
                        )
                        err_base = _fallback

                    err_dir = os.path.join(err_base, "errors", process_type)
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
                    print(f"[error dump] saved to: {err_dir}")
                except Exception as dump_err:
                    print(f"[error dump] could not save error files: {dump_err}")

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

        # If some files succeeded but others failed, include warnings as a header
        response_obj = None
        # If some files succeeded but others failed, include warnings as a header
        response_obj = None
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
        traceback.print_exc()
        return f"An error occurred: {str(e)}", 500


def run_app(host: str = "0.0.0.0", port: int = 5000, debug: bool = False) -> None:
    """Helper so other modules can host the Flask app."""
    app.run(debug=debug, host=host, port=port)


if __name__ == "__main__":
    run_app(debug=True)
