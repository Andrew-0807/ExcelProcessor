document.addEventListener('DOMContentLoaded', () => {
  // Get references to DOM elements
  const processBtn = document.getElementById('processBtn');
  const fileInput = document.getElementById('fileInput');
  const dropArea = document.getElementById('drop-area');
  
  if (!processBtn || !fileInput || !dropArea) {
    console.error('Required elements not found. Make sure your HTML has elements with IDs "processBtn", "fileInput", and "drop-area"');
    return;
  }

  // Prevent default drag behaviors
  ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropArea.addEventListener(eventName, preventDefaults, false);
    document.body.addEventListener(eventName, preventDefaults, false);
  });

  // Highlight drop area when item is dragged over it
  ['dragenter', 'dragover'].forEach(eventName => {
    dropArea.addEventListener(eventName, highlight, false);
  });

  ['dragleave', 'drop'].forEach(eventName => {
    dropArea.addEventListener(eventName, unhighlight, false);
  });

  // Handle dropped files
  dropArea.addEventListener('drop', handleDrop, false);

  // Handle click to open file dialog
  dropArea.addEventListener('click', () => {
    fileInput.click();
  });

  // Update file input change handler
  fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) {
      updateDropAreaText(fileInput.files.length);
    }
  });

  function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
  }

  function highlight(e) {
    dropArea.classList.add('dragover');
  }

  function unhighlight(e) {
    dropArea.classList.remove('dragover');
  }

  function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    fileInput.files = files;
    updateDropAreaText(files.length);
  }

  function updateDropAreaText(fileCount) {
    const p = dropArea.querySelector('p');
    if (fileCount === 1) {
      p.textContent = `1 file selected - Ready to process!`;
    } else if (fileCount > 1) {
      p.textContent = `${fileCount} files selected - Ready to process!`;
    } else {
      p.textContent = 'Drag & Drop your files here';
    }
  }

  processBtn.addEventListener('click', () => {
    const files = fileInput.files;
    const processType = document.querySelector('input[name="process_type"]:checked').value;
    console.log('Processing files...');
    
    if (!files.length) {
      alert('Please select a file.');
      return;
    }
  
    // Show loading state
    const originalText = processBtn.textContent;
    processBtn.innerHTML = '<span class="loading"></span> Processing...';
    processBtn.disabled = true;
  
    const formData = new FormData();
    // Append all files to support multiple file uploads
    for (let i = 0; i < files.length; i++) {
        formData.append('file', files[i]);
    }
    formData.append('process_type', processType);
  
    fetch('/process', {
      method: 'POST',
      body: formData
    })
    .then(response => {
      if (!response.ok) throw new Error('Network response was not OK');
      
      // Extract filename from Content-Disposition header
      const disposition = response.headers.get('Content-Disposition');
      let filename = files[0].name; // fallback to original filename
      
      if (disposition) {
        // More robust filename extraction
        const filenameMatch = disposition.match(/filename\*?=['"]?(?:UTF-\d['"]*)?([^;\r\n"']*)['"]?;?/i);
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1];
          console.log('Extracted filename:', filename);
        }
      }
      
      return response.blob().then(blob => ({ blob, filename }));
    })
    .then(({ blob, filename }) => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      setTimeout(() => {
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
      }, 100);
      
      // Show success message
      showMessage('Files processed successfully!', 'success');
    })
    .catch(err => {
      console.error('Error processing file:', err);
      alert('Error processing file: ' + err.message);
      showMessage('Error processing files. Please try again.', 'error');
    })
    .finally(() => {
      // Reset button state
      processBtn.textContent = originalText;
      processBtn.disabled = false;
    });
  });

  function showMessage(text, type) {
    // Remove any existing messages
    const existingMessage = document.querySelector('.message');
    if (existingMessage) {
      existingMessage.remove();
    }

    // Create new message element
    const message = document.createElement('div');
    message.className = `message ${type}`;
    message.textContent = text;
    
    // Insert after the mode selection
    const modeSelection = document.querySelector('.mode-selection');
    modeSelection.parentNode.insertBefore(message, modeSelection.nextSibling);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
      if (message.parentNode) {
        message.remove();
      }
    }, 5000);
  }
});
  