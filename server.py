from flask import Flask, render_template, request, send_file
import pandas as pd
import io
import os
import sys
import traceback
import zipfile  # Add this import
from app_info import __version__

try:
    # Import the processor modules
    from classes.valoare_sgr import SGRValueProcessor
    from classes.valoare_minus import ValoareMinus
    from classes.format_add_column import FormatAddColumn
    from classes.excel_data_extractor import ExcelDataExtractor
    
    # Import new processing modules
    from borderou.main import BorderouPipeline
    from CardCec.pos_processor import process_pos_file, detect_pos_type
except Exception as e:
    print(f"Error importing modules: {str(e)}")

# Get the base path for templates and static files
# This handles both normal execution and PyInstaller frozen execution
if getattr(sys, 'frozen', False):
    # Running as a PyInstaller bundle
    base_path = sys._MEIPASS
else:
    # Running normally
    base_path = os.path.dirname(os.path.abspath(__file__))

# Initialize Flask with correct paths
app = Flask(__name__,
            template_folder=os.path.join(base_path, 'templates'),
            static_folder=os.path.join(base_path, 'static'))


def create_app() -> Flask:
    """Expose the Flask application for external runners."""
    return app


def _valid_excel(filename: str) -> bool:
    return filename.endswith('.xlsx') or filename.endswith('.xls')


@app.route('/')
def index():
    return render_template('index.html', app_version=__version__)


@app.route('/process', methods=['POST'])
def process_file():
    files = request.files.getlist('file')  # Get all uploaded files
    process_type = request.form['process_type']

    try:
        outputs: list[io.BytesIO] = []
        filenames: list[str] = []
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
                df = pd.read_excel(file, engine='openpyxl')
                df.name = file.filename

                # Process the data based on the process_type
                if process_type == 'adaos':
                    processor = FormatAddColumn()
                    result_df = processor.process_dataframe(df)
                elif process_type == 'sgr':
                    processor = SGRValueProcessor()
                    result_df = processor.process_dataframe(df)
                elif process_type == 'minus':
                    processor = ValoareMinus()
                    result_df = processor.process_dataframe(df)
                elif process_type == 'extract':
                    processor = ExcelDataExtractor()
                    result_df = processor.process_dataframe(df)
                elif process_type == 'borderou':
                    # Handle borderou processing - save file temporarily and process through pipeline
                    temp_file_path = f"temp_{file.filename}"
                    with open(temp_file_path, 'wb') as temp_file:
                        file.seek(0)
                        temp_file.write(file.read())
                    
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
                                    result_df.to_excel(output, index=False, engine='openpyxl')
                                    output.seek(0)
                                    outputs.append(output)
                                    filenames.append(f"borderou_{os.path.basename(xlsx_file)}")
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
                elif process_type == 'cardcec':
                    # Save the uploaded file temporarily
                    temp_file_path = f"temp_{file.filename}"
                    with open(temp_file_path, 'wb') as temp_file:
                        file.seek(0)
                        temp_file.write(file.read())
                    
                    try:
                        # Process the file with the new POS processor
                        temp_output_path = f"processed_{file.filename}"
                        pos_type = detect_pos_type(file.filename)
                        process_pos_file(temp_file_path, temp_output_path, pos_type)
                        
                        # Read the processed file back into a DataFrame
                        result_df = pd.read_csv(temp_output_path)
                        
                        # Clean up temp files
                        if os.path.exists(temp_output_path):
                            os.remove(temp_output_path)
                    except Exception as e:
                        print(f"Error processing {file.filename} with POS processor: {e}")
                        raise
                    finally:
                        # Clean up the temp file
                        if os.path.exists(temp_file_path):
                            os.remove(temp_file_path)
                else:
                    return "Invalid process type", 400

                # Save the processed DataFrame to a BytesIO object
                output = io.BytesIO()
                result_df.to_excel(output, index=False, engine='openpyxl')
                output.seek(0)
                outputs.append(output)
                # Save the filename for the zip
                original_filename = file.filename
                processed_filename = f"{process_type} - {original_filename}"
                filenames.append(processed_filename)
            except Exception as e:
                print(f"Error reading {file.filename}: {e}")
                continue

        # These lines should be OUTSIDE the for loop!
        if len(outputs) == 1:
            return send_file(outputs[0], download_name=filenames[0], as_attachment=True)

        # If multiple files, zip them
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zipf:
            for output, fname in zip(outputs, filenames):
                output.seek(0)
                zipf.writestr(fname, output.read())
        zip_buffer.seek(0)
        return send_file(
            zip_buffer,
            download_name="processed_files.zip",
            as_attachment=True,
            mimetype='application/zip'
        )

    except Exception as e:
        traceback.print_exc()
        return f"An error occurred: {str(e)}", 500


def run_app(host: str = '0.0.0.0', port: int = 5000, debug: bool = False) -> None:
    """Helper so other modules can host the Flask app."""
    app.run(debug=debug, host=host, port=port)


if __name__ == '__main__':
    run_app(debug=True)
