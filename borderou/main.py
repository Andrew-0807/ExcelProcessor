#!/usr/bin/env python3
"""
Main Pipeline Script for Borderou Processing
============================================

This script processes files through the complete pipeline:
1. Excel to CSV conversion (using to_csv module)
2. CSV cleaning and standardization (using csv_cleaner module)
3. Import format transformation (using borderou_to_import_transformer module)

Directory Structure:
- Input: ./main/in (Excel files)
- Output: ./main/out (Final import-ready CSV files)

Usage: python main.py
"""

import os
import sys
from datetime import datetime

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import functions from existing modules
from to_csv import excel_to_csv
from csv_cleaner import transform_borderou_csv
from borderou_to_import_transformer import transform_borderou_to_import_format
from csv_to_xlsx_converter import CSVToXLSXConverter


class BorderouPipeline:
    """Complete pipeline for processing Borderou files from Excel to import format"""
    
    def __init__(self, input_dir="./main/in", output_dir="./main/out"):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.temp_dir = os.path.join(output_dir, "temp")
        
        # Create directory structure
        self.setup_directories()
        
    def setup_directories(self):
        """Create necessary directories"""
        directories = [
            self.input_dir,
            self.output_dir,
            self.temp_dir,
            os.path.join(self.temp_dir, "csv"),
            os.path.join(self.temp_dir, "cleaned"),
            os.path.join(self.temp_dir, "import_csv"),  # New directory for CSV files before XLSX conversion
            os.path.join(self.output_dir, "import"),
            os.path.join(self.output_dir, "import", "csv")  # CSV subfolder in import directory
        ]
        
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)
                print(f"📁 Created directory: {directory}")
    
    def convert_csv_to_xlsx(self, csv_files):
        """Convert CSV files to XLSX format"""
        print("\n📊 Step 4: Converting CSV files to XLSX format...")
        
        # Create directories for the conversion
        import_csv_dir = os.path.join(self.temp_dir, "import_csv")
        xlsx_output_dir = os.path.join(self.output_dir, "import")
        csv_output_dir = os.path.join(self.output_dir, "import", "csv")  # CSV subfolder
        
        # Initialize the converter
        converter = CSVToXLSXConverter()
        
        # Copy CSV files to import_csv directory first
        import shutil
        copied_files = []
        
        if isinstance(csv_files, list):
            # Multiple files (M1/M2 case)
            for csv_file in csv_files:
                if os.path.exists(csv_file):
                    dest_path = os.path.join(import_csv_dir, os.path.basename(csv_file))
                    shutil.copy2(csv_file, dest_path)
                    copied_files.append(dest_path)
                    print(f"   📄 Copied: {os.path.basename(csv_file)}")
        else:
            # Single file (M3 case)
            if os.path.exists(csv_files):
                dest_path = os.path.join(import_csv_dir, os.path.basename(csv_files))
                shutil.copy2(csv_files, dest_path)
                copied_files.append(dest_path)
                print(f"   📄 Copied: {os.path.basename(csv_files)}")
        
        if not copied_files:
            print("❌ No CSV files to convert")
            return []
        
        # Convert CSV files to XLSX and save CSV files to the CSV subfolder
        print(f"🔄 Converting {len(copied_files)} CSV file(s) to XLSX...")
        
        xlsx_files = []
        csv_final_files = []
        for csv_file in copied_files:
            try:
                # Generate XLSX filename
                base_name = os.path.splitext(os.path.basename(csv_file))[0]
                xlsx_filename = f"{base_name}.xlsx"
                xlsx_path = os.path.join(xlsx_output_dir, xlsx_filename)
                
                # Copy CSV file to final CSV location
                csv_final_path = os.path.join(csv_output_dir, os.path.basename(csv_file))
                shutil.copy2(csv_file, csv_final_path)
                csv_final_files.append(csv_final_path)
                
                # Convert single file
                success = converter.convert_csv_to_xlsx(csv_file, xlsx_path)
                if success:
                    xlsx_files.append(xlsx_path)
                    print(f"   ✅ Converted: {xlsx_filename}")
                else:
                    print(f"   ❌ Failed to convert: {os.path.basename(csv_file)}")
            except Exception as e:
                print(f"   ❌ Error converting {os.path.basename(csv_file)}: {str(e)}")
        
        return xlsx_files
    
    def process_file(self, excel_file_path):
        """Process a single Excel file through the complete pipeline"""
        print(f"\n🚀 Processing: {os.path.basename(excel_file_path)}")
        print("=" * 60)
        
        try:
            # Step 1: Excel to CSV (using to_csv module)
            print("📄 Step 1: Converting Excel to CSV...")
            csv_output_dir = os.path.join(self.temp_dir, "csv")
            excel_to_csv(excel_file_path, csv_output_dir)
            
            # Generate CSV file path
            base_name = os.path.basename(excel_file_path)
            file_name_without_ext = os.path.splitext(base_name)[0]
            csv_path = os.path.join(csv_output_dir, f"{file_name_without_ext}.csv")
            
            if not os.path.exists(csv_path):
                print(f"❌ CSV file not created: {csv_path}")
                return None
            
            # Step 2: Clean CSV (using csv_cleaner module)
            print("🧹 Step 2: Cleaning CSV data...")
            cleaned_output_dir = os.path.join(self.temp_dir, "cleaned")
            cleaned_output_path = os.path.join(cleaned_output_dir, f"{file_name_without_ext}_cleaned.csv")
            
            cleaned_df, cleaned_path = transform_borderou_csv(csv_path, cleaned_output_path)
            
            if not os.path.exists(cleaned_path):
                print(f"❌ Cleaned CSV file not created: {cleaned_path}")
                return None
            
            # Step 3: Transform to import format (using borderou_to_import_transformer module)
            print("🔄 Step 3: Transforming to import format...")
            csv_output_dir = os.path.join(self.output_dir, "import", "csv")  # Save CSV to subfolder
            import_output_path = os.path.join(csv_output_dir, f"import_bon_fiscal_{file_name_without_ext}_cleaned.csv")
            
            result = transform_borderou_to_import_format(cleaned_path, import_output_path)
            
            # Handle both single file and multiple file outputs
            if isinstance(result, list):
                # M1/M2 files - multiple outputs
                output_files = result
                print(f"🎉 Step 3 completed successfully for {os.path.basename(excel_file_path)}")
                print(f"📁 Split into {len(output_files)} files:")
                csv_files = []
                for import_path, transformed_df in output_files:  # Fixed order: path first, df second
                    if not os.path.exists(import_path):
                        print(f"❌ Import file not created: {import_path}")
                        return None
                    print(f"   📄 {os.path.basename(import_path)}")
                    csv_files.append(import_path)
                
                # Step 4: Convert CSV files to XLSX
                xlsx_files = self.convert_csv_to_xlsx(csv_files)
                if not xlsx_files:
                    print(f"❌ Failed to convert CSV files to XLSX for {os.path.basename(excel_file_path)}")
                    return None
                
                print(f"🎉 Pipeline completed successfully for {os.path.basename(excel_file_path)}")
                return xlsx_files
            else:
                # Single file output (M3 and other patterns)
                transformed_df, import_path = result
                if not os.path.exists(import_path):
                    print(f"❌ Import file not created: {import_path}")
                    return None
                
                print(f"🎉 Step 3 completed successfully for {os.path.basename(excel_file_path)}")
                print(f"📁 Final CSV output: {os.path.basename(import_path)}")
                
                # Step 4: Convert CSV file to XLSX
                xlsx_files = self.convert_csv_to_xlsx(import_path)
                if not xlsx_files:
                    print(f"❌ Failed to convert CSV file to XLSX for {os.path.basename(excel_file_path)}")
                    return None
                
                print(f"🎉 Pipeline completed successfully for {os.path.basename(excel_file_path)}")
                print(f"📁 Final XLSX output: {os.path.basename(xlsx_files[0])}")
                return xlsx_files[0]
            
        except Exception as e:
            print(f"❌ Error processing {excel_file_path}: {str(e)}")
            return None
    
    def run_pipeline(self):
        """Run the complete pipeline for all Excel files in input directory"""
        print("🔥 Starting Borderou Processing Pipeline")
        print("=" * 60)
        print(f"📁 Input directory: {self.input_dir}")
        print(f"📁 Output directory: {self.output_dir}")
        
        # Check if input directory exists
        if not os.path.exists(self.input_dir):
            print(f"⚠️  Input directory does not exist: {self.input_dir}")
            print("Creating input directory...")
            os.makedirs(self.input_dir, exist_ok=True)
            print("📁 Please place your Excel files in the input directory and run again.")
            return
        
        # Find all Excel files
        excel_files = []
        for root, _, files in os.walk(self.input_dir):
            for file in files:
                if file.endswith(('.xlsx', '.xls')):
                    excel_files.append(os.path.join(root, file))
        
        if not excel_files:
            print("⚠️  No Excel files found in input directory!")
            print(f"📁 Please place Excel files in: {self.input_dir}")
            return
        
        print(f"🔍 Found {len(excel_files)} Excel file(s) to process")
        
        processed_files = []
        failed_files = []
        
        # Process each file
        for excel_file in excel_files:
            try:
                result = self.process_file(excel_file)
                if result:
                    processed_files.append(result)
                else:
                    failed_files.append(excel_file)
            except Exception as e:
                print(f"❌ Failed to process {excel_file}: {str(e)}")
                failed_files.append(excel_file)
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 PIPELINE SUMMARY")
        print("=" * 60)
        print(f"✅ Successfully processed: {len(processed_files)} files")
        print(f"❌ Failed to process: {len(failed_files)} files")
        
        if processed_files:
            print("\n📁 Generated XLSX files:")
            for file_result in processed_files:
                # Handle both single files (strings) and multiple files (lists)
                if isinstance(file_result, list):
                    for file_path in file_result:
                        print(f"   • {os.path.basename(file_path)}")
                else:
                    print(f"   • {os.path.basename(file_result)}")
        
        if failed_files:
            print("\n⚠️  Failed files:")
            for file_path in failed_files:
                print(f"   • {os.path.basename(file_path)}")
        
        print(f"\n🎯 Final XLSX files are in: {os.path.join(self.output_dir, 'import')}")
        print(f"📁 Final CSV files are in: {os.path.join(self.output_dir, 'import', 'csv')}")
        print(f"📁 Intermediate CSV files are in: {os.path.join(self.temp_dir, 'import_csv')}")


def main():
    """Main function to run the pipeline"""
    try:
        pipeline = BorderouPipeline()
        pipeline.run_pipeline()
    except KeyboardInterrupt:
        print("\n⚠️  Pipeline interrupted by user")
    except Exception as e:
        print(f"❌ Pipeline failed: {str(e)}")


if __name__ == "__main__":
    main()