import pandas as pd
import os

def excel_to_csv(excel_file_path, output_folder):
    df = pd.read_excel(excel_file_path)
    base_name = os.path.basename(excel_file_path)
    file_name_without_ext = os.path.splitext(base_name)[0]
    csv_file_path = os.path.join(output_folder, f"{file_name_without_ext}.csv")
    df.to_csv(csv_file_path, index=False)
    print(f"Converted {excel_file_path} to {csv_file_path}")

input_directories = [
    # r"e:\Programming\Trae - MomAutomations\NewFeatureTest\base-out",
    r"e:\Programming\Trae - MomAutomations\NewFeatureTest\in\toCSV"
]

output_directory = r"e:\Programming\Trae - MomAutomations\NewFeatureTest\out\CSV"

if not os.path.exists(output_directory):
    os.makedirs(output_directory)

for input_dir in input_directories:
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.endswith(".xlsx"):
                excel_file_path = os.path.join(root, file)
                excel_to_csv(excel_file_path, output_directory)