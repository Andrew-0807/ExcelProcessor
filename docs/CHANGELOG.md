# Changelog

All notable changes to Excel Processor will be documented in this file.

## [1.1.1] - 2025-11-15

### ✨ New Features
- **Drag and Drop Functionality**: Complete drag and drop file upload support
- **Visual Feedback**: Drop area highlights when dragging files over it
- **Click-to-Browse**: Click the drop area to open traditional file dialog
- **Dynamic File Count**: Shows "X files selected - Ready to process!"
- **Loading States**: Button shows spinning animation during processing
- **Success/Error Messages**: Beautiful animated messages with auto-dismiss
- **Multiple File Support**: Handle multiple files at once

### 🎨 UX Improvements
- Enhanced user interaction with smooth animations
- Professional loading states and visual feedback
- Intuitive drag and drop interface
- Clear status indicators for file selection
- Seamless integration with existing beautiful UI

### 🔧 Technical Updates
- Prevents default browser drag behaviors
- Handles all drag events (enter, over, leave, drop)
- Dynamic file input updates
- Enhanced error handling and cleanup
- Improved button state management

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
4. Access the enhanced interface at `http://127.0.0.1:5000`

## New Usage
- **Drag and drop files** directly onto the drop area
- **Click the drop area** to browse for files
- **Select processing type** from the beautiful radio buttons
- **Watch the loading animation** while processing
- **Enjoy success messages** when files are processed!
