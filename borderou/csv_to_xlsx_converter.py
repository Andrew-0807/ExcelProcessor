import pandas as pd
import os
import sys
from datetime import datetime
from pathlib import Path

class CSVToXLSXConverter:
    """
    A utility class to convert CSV files to XLSX format with configurable input and output directories.
    """
    
    def __init__(self, input_dir="./input", output_dir="./output"):
        """
        Initialize the converter with input and output directories.
        
        Args:
            input_dir (str): Directory containing CSV files to convert
            output_dir (str): Directory where XLSX files will be saved
        """
        self.input_dir = os.path.abspath(input_dir)
        self.output_dir = os.path.abspath(output_dir)
        self.setup_directories()
    
    def setup_directories(self):
        """Create output directory if it doesn't exist."""
        os.makedirs(self.output_dir, exist_ok=True)
        print(f"📁 Input directory: {self.input_dir}")
        print(f"📁 Output directory: {self.output_dir}")
    
    def convert_csv_to_xlsx(self, csv_file_path, xlsx_file_path):
        """
        Convert a single CSV file to XLSX format.
        
        Args:
            csv_file_path (str): Path to the input CSV file
            xlsx_file_path (str): Path for the output XLSX file
            
        Returns:
            bool: True if conversion successful, False otherwise
        """
        try:
            # Read CSV file
            df = pd.read_csv(csv_file_path, encoding='utf-8')
            
            # Write to XLSX format
            with pd.ExcelWriter(xlsx_file_path, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Sheet1')
            
            print(f"✅ Converted: {os.path.basename(csv_file_path)} → {os.path.basename(xlsx_file_path)}")
            return True
            
        except UnicodeDecodeError:
            # Try different encodings if UTF-8 fails
            try:
                df = pd.read_csv(csv_file_path, encoding='latin-1')
                with pd.ExcelWriter(xlsx_file_path, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Sheet1')
                print(f"✅ Converted (latin-1): {os.path.basename(csv_file_path)} → {os.path.basename(xlsx_file_path)}")
                return True
            except Exception as e:
                print(f"❌ Encoding error for {os.path.basename(csv_file_path)}: {str(e)}")
                return False
                
        except Exception as e:
            print(f"❌ Error converting {os.path.basename(csv_file_path)}: {str(e)}")
            return False
    
    def convert_all_csv_files(self):
        """
        Convert all CSV files in the input directory to XLSX format.
        
        Returns:
            dict: Summary of conversion results
        """
        print("🔄 Starting CSV to XLSX conversion...")
        print("=" * 60)
        
        # Check if input directory exists
        if not os.path.exists(self.input_dir):
            print(f"❌ Input directory does not exist: {self.input_dir}")
            return {"success": 0, "failed": 0, "files": []}
        
        # Find all CSV files
        csv_files = []
        for root, _, files in os.walk(self.input_dir):
            for file in files:
                if file.lower().endswith('.csv'):
                    csv_files.append(os.path.join(root, file))
        
        if not csv_files:
            print("⚠️  No CSV files found in input directory!")
            return {"success": 0, "failed": 0, "files": []}
        
        print(f"🔍 Found {len(csv_files)} CSV file(s) to convert")
        
        successful_conversions = []
        failed_conversions = []
        
        # Convert each CSV file
        for csv_file in csv_files:
            # Generate output filename
            csv_filename = os.path.basename(csv_file)
            xlsx_filename = os.path.splitext(csv_filename)[0] + '.xlsx'
            xlsx_file_path = os.path.join(self.output_dir, xlsx_filename)
            
            # Convert the file
            if self.convert_csv_to_xlsx(csv_file, xlsx_file_path):
                successful_conversions.append({
                    'input': csv_file,
                    'output': xlsx_file_path,
                    'filename': xlsx_filename
                })
            else:
                failed_conversions.append(csv_file)
        
        # Print summary
        self.print_summary(successful_conversions, failed_conversions)
        
        return {
            "success": len(successful_conversions),
            "failed": len(failed_conversions),
            "files": successful_conversions
        }
    
    def print_summary(self, successful_conversions, failed_conversions):
        """Print conversion summary."""
        print("\n" + "=" * 60)
        print("📊 CONVERSION SUMMARY")
        print("=" * 60)
        print(f"✅ Successfully converted: {len(successful_conversions)} files")
        print(f"❌ Failed to convert: {len(failed_conversions)} files")
        
        if successful_conversions:
            print("\n📁 Generated XLSX files:")
            for conversion in successful_conversions:
                print(f"   • {conversion['filename']}")
        
        if failed_conversions:
            print("\n⚠️  Failed files:")
            for file_path in failed_conversions:
                print(f"   • {os.path.basename(file_path)}")
        
        print(f"\n🎯 XLSX files are saved in: {self.output_dir}")


def main():
    """Main function to run the CSV to XLSX converter."""
    print("🔥 CSV to XLSX Converter")
    print("=" * 60)
    
    # Default directories
    default_input = "./input"
    default_output = "./output"
    
    # Check for command line arguments
    if len(sys.argv) >= 2:
        input_dir = sys.argv[1]
    else:
        input_dir = default_input
    
    if len(sys.argv) >= 3:
        output_dir = sys.argv[2]
    else:
        output_dir = default_output
    
    # Create converter instance and run conversion
    converter = CSVToXLSXConverter(input_dir, output_dir)
    results = converter.convert_all_csv_files()
    
    # Exit with appropriate code
    if results["failed"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()