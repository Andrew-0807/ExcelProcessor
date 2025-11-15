# Changelog

All notable changes to Excel Processor will be documented in this file.

## [1.1.0] - 2025-11-15

### 🚀 Major Features Added
- **Borderou Processing Pipeline**: Complete Excel → CSV → Cleaning → Import Format → XLSX processing
- **CardCec CSV Transformer**: Payment data processing for FAST-FOOD locations
- **Beautiful UI Redesign**: Modern gradient design with glass-morphism effects

### ✨ New Features
- Integrated Borderou processing with support for M1/M2 file splitting
- Added CardCec processing for payment data transformation
- Pattern-based file processing for various business units
- Modern responsive frontend with smooth animations
- Enhanced drop area with visual feedback
- Custom styled radio buttons and interactive elements

### 🔧 Technical Improvements
- Enhanced Flask server with new processing routes
- Improved file handling and temporary file cleanup
- Better error handling and user feedback
- Updated version system
- Professional typography with Inter font
- Mobile-responsive design

### 📋 Processing Options
- Adaos
- SGR
- Minus
- Extract
- Borderou (NEW)
- CardCec (NEW)

## [1.0.2] - Previous Version
- Basic Excel processing functionality
- Simple UI design
- Core processing modules (Adaos, SGR, Minus, Extract)

---

## Upgrade Instructions
1. Pull the latest changes: `git pull origin main`
2. Install any new dependencies if required
3. Restart the Flask server
4. Access the new beautiful interface at `http://127.0.0.1:5000`

## New Usage
- Select "Borderou" for processing borderou Excel files through the complete pipeline
- Select "CardCec" for processing payment data CSV files
- Enjoy the new modern, beautiful interface!
