# CSV Transformer for FAST-FOOD Data

A flexible Python tool to transform FAST-FOOD payment data from input format to standardized accounting output format.

## Features

- **Pattern Matching System**: Automatically detects file types and applies appropriate transformation rules
- **Flexible Configuration**: Easy to add new patterns for different FAST-FOOD locations or formats
- **Data Formatting**: Converts input data into a manageable structure
- **VAT Calculation**: Handles multiple VAT rates (21%, 11%) with configurable calculation methods
- **Complete Output**: Generates all 62 required columns, preserving empty columns for compatibility

## Files Structure

```
CardCec/
├── enhanced_csv_transformer.py    # Main transformer class
├── usage_example.py              # Usage examples and pattern management
├── csv_transformer.py            # Basic transformer (legacy)
├── out/
│   ├── FAST-FOOD 1 - in.csv      # Input file
│   ├── FAST-FOOD 1 - final.csv   # Generated output
│   └── import-out.csv            # Reference output format
└── README.md                     # This file
```

## Quick Start

```python
from enhanced_csv_transformer import EnhancedCSVTransformer

# Initialize transformer
transformer = EnhancedCSVTransformer()

# Transform a file (pattern automatically detected)
result = transformer.transform_to_output(
    'out/FAST-FOOD 1 - in.csv',
    'out/FAST-FOOD 1 - output.csv'
)

print(f"Generated {len(result)} rows")
```

## Input File Format

The input files should contain:
- `Nr. Z`: Transaction ID
- `Data Ultimei Incasari`: Date and time
- `Tip Incasare`: Payment type (CARD, CEC, NUMERAR)
- `Valoare`: Amount

## Output File Format

Generates 62 columns including:
- Document information (Serie document, Numar document, Data document)
- Payment breakdown (Card, Cont casa, Numerar)
- VAT calculations (21% and 11% rates)
- All accounting fields with proper codes

## Adding New Patterns

```python
# Define a new pattern
new_pattern = {
    'file_pattern': r'YOUR_PATTERN\.csv',
    'columns': {
        'transaction_id': 'Your Transaction Column',
        'date': 'Your Date Column',
        'payment_type': 'Your Payment Type Column',
        'amount': 'Your Amount Column'
    },
    'payment_mapping': {
        'CARD': 'Card',
        'CEC': 'Cont casa',
        'NUMERAR': 'Numerar'
    },
    'vat_calculation_method': 'reverse_from_sample',
    'output_format': {
        # ... configuration
    }
}

# Add the pattern
transformer.add_pattern('NEW_PATTERN', new_pattern)
```

## Pattern Configuration

Each pattern includes:

- **file_pattern**: Regex pattern to match filenames
- **columns**: Mapping of input column names to standard names
- **payment_mapping**: How to map payment types to output columns
- **vat_calculation_method**: Method for calculating VAT splits
- **output_format**: Fixed values and VAT configuration

## VAT Calculation Methods

- `reverse_from_sample`: Based on analysis of sample output data
- `standard`: Standard VAT calculation (base = total / (1 + rate))

## Usage Examples

Run the usage example to see the transformer in action:

```bash
python usage_example.py
```

This will:
1. Transform FAST-FOOD 1 data
2. Add a FAST-FOOD 2 pattern
3. List all available patterns

## Extending for Multiple Locations

The system is designed to handle multiple FAST-FOOD locations:

1. Create patterns for each location/variation
2. Use `add_pattern()` to register them
3. The transformer will automatically detect and apply the correct pattern

## Error Handling

The transformer includes comprehensive error handling:
- Pattern detection failures
- Missing columns
- Invalid data formats
- File I/O errors

## Dependencies

- pandas
- Python 3.7+

## License

This tool is part of the CardCec automation system.
