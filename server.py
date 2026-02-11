from flask import Flask, render_template, request, send_file
import pandas as pd
import io
import os
import sys
import tempfile
import traceback
import zipfile
from app_info import __version__

try:
    # Import processor modules
    from processors.core.classes.valoare_sgr import SGRValueProcessor
    from processors.core.classes.valoare_minus import ValoareMinus
    from processors.core.classes.format_add_column import FormatAddColumn
    from processors.core.classes.excel_data_extractor import ExcelDataExtractor

    # Import new processing modules
    from processors.borderou.main import BorderouPipeline
    from processors.cardcec.CardCec.pos_processor import (
        process_pos_file,
        detect_pos_type,
    )

    # Import sales transform module
    from processors.sales_transform.sales_transform import SalesTransformProcessor
except Exception as e:
    print(f"Error importing modules: {str(e)}")

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


def _valid_excel(filename: str) -> bool:
    return filename.endswith(".xlsx") or filename.endswith(".xls")


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
            # Check if the file has a valid Excel extension
            if not _valid_excel(file.filename):
                print(f"Skipping non-Excel file: {file.filename}")
                continue
            # Check if the file is not empty
            file.seek(0, io.SEEK_END)
            file_length = file.tell()
            file.seek(0)
            if file_length == 0:
                print(f"Skipping empty file: {file.filename}")
                continue

            try:
                df = pd.read_excel(file, engine="openpyxl")
                df.name = file.filename

                # Process the data based on the process_type
                if process_type == "adaos":
                    processor = FormatAddColumn()
                    result_df = processor.process_dataframe(df)
                elif process_type == "sgr":
                    processor = SGRValueProcessor()
                    result_df = processor.process_dataframe(df)
                elif process_type == "minus":
                    processor = ValoareMinus()
                    result_df = processor.process_dataframe(df)
                elif process_type == "extract":
                    processor = ExcelDataExtractor()
                    result_df = processor.process_dataframe(df)
                elif process_type == "borderou":
                    # Handle borderou processing - save file temporarily and process through pipeline
                    fd, temp_file_path = tempfile.mkstemp(suffix=".xlsx")
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
                        pipeline = BorderouPipeline()
                        result = pipeline.process_file(temp_file_path)

                        if result:
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
                        # Clean up temp file
                        if os.path.exists(temp_file_path):
                            os.remove(temp_file_path)
                elif process_type == "cardcec":
                    # Save the uploaded file temporarily with unique name
                    fd, temp_file_path = tempfile.mkstemp(suffix=".xlsx")
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
                        process_pos_file(temp_file_path, temp_output_path, pos_type)

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
                processed_filename = f"{process_type} - {original_filename}"
                filenames.append(processed_filename)
            except Exception as e:
                error_msg = f"Error processing {file.filename}: {e}"
                print(error_msg)
                traceback.print_exc()
                errors.append(error_msg)
                continue

        # These lines should be OUTSIDE the for loop!
        if not outputs and errors:
            error_detail = "\n".join(errors)
            return f"Processing failed for all files:\n{error_detail}", 500

        if not outputs:
            return "No valid files were provided for processing.", 400

        if len(outputs) == 1:
            return send_file(outputs[0], download_name=filenames[0], as_attachment=True)

        # If multiple files, zip them
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zipf:
            for output, fname in zip(outputs, filenames):
                output.seek(0)
                zipf.writestr(fname, output.read())
        zip_buffer.seek(0)
        return send_file(
            zip_buffer,
            download_name="processed_files.zip",
            as_attachment=True,
            mimetype="application/zip",
        )

    except Exception as e:
        traceback.print_exc()
        return f"An error occurred: {str(e)}", 500


def run_app(host: str = "0.0.0.0", port: int = 5000, debug: bool = False) -> None:
    """Helper so other modules can host the Flask app."""
    app.run(debug=debug, host=host, port=port)


if __name__ == "__main__":
    run_app(debug=True)
