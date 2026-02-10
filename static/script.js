document.addEventListener('DOMContentLoaded', () => {
  // Get references to DOM elements
  const processBtn = document.getElementById('processBtn');
  const fileInput = document.getElementById('fileInput');
  const dropArea = document.getElementById('drop-area');
  const helpBtn = document.getElementById('helpBtn');
  const helpModal = document.getElementById('help-modal');
  const modalCloseBtns = document.querySelectorAll('.modal-close, .modal-close-btn');
  const fileList = document.getElementById('file-list');
  
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
      displayFileList(fileInput.files);
    }
  });

  // Help modal functionality
  if (helpBtn && helpModal) {
    helpBtn.addEventListener('click', () => {
      helpModal.classList.add('show');
      helpModal.setAttribute('aria-hidden', 'false');
    });

    // Close modal when clicking close buttons
    modalCloseBtns.forEach(btn => {
      btn.addEventListener('click', closeModal);
    });

    // Close modal when clicking overlay
    const modalOverlay = helpModal.querySelector('.modal-overlay');
    if (modalOverlay) {
      modalOverlay.addEventListener('click', closeModal);
    }

    // Close modal with Escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && helpModal.classList.contains('show')) {
        closeModal();
      }
    });
  }

  function closeModal() {
    helpModal.classList.remove('show');
    helpModal.setAttribute('aria-hidden', 'true');
  }

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
    displayFileList(files);
  }

  function updateDropAreaText(fileCount) {
    const mainText = dropArea.querySelector('.main-text');
    const subText = dropArea.querySelector('.sub-text');
    
    if (fileCount === 1) {
      mainText.textContent = `1 file selected - Ready to process!`;
      subText.textContent = 'Click to add more files or change selection';
    } else if (fileCount > 1) {
      mainText.textContent = `${fileCount} files selected - Ready to process!`;
      subText.textContent = 'Click to add more files or change selection';
    } else {
      mainText.textContent = 'Drag & Drop your files here';
      subText.textContent = 'or click to browse';
    }
  }

  function displayFileList(files) {
    if (!fileList) return;
    
    fileList.innerHTML = '';
    
    Array.from(files).forEach(file => {
      const fileItem = document.createElement('div');
      fileItem.className = 'file-item';
      fileItem.setAttribute('role', 'listitem');
      
      const fileName = document.createElement('span');
      fileName.className = 'file-name';
      fileName.textContent = file.name;
      
      const fileSize = document.createElement('span');
      fileSize.className = 'file-size';
      fileSize.textContent = formatFileSize(file.size);
      
      fileItem.appendChild(fileName);
      fileItem.appendChild(fileSize);
      fileList.appendChild(fileItem);
    });
  }

  function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  processBtn.addEventListener('click', () => {
    const files = fileInput.files;
    const processType = document.querySelector('input[name="process_type"]:checked').value;
    console.log('Processing files...');
    
    if (!files.length) {
      showMessage('Please select a file.', 'error');
      return;
    }
  
    // Show loading state
    const originalContent = processBtn.innerHTML;
    processBtn.classList.add('loading');
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
      showMessage('Error processing files. Please try again.', 'error');
    })
    .finally(() => {
      // Reset button state
      processBtn.classList.remove('loading');
      processBtn.innerHTML = originalContent;
      processBtn.disabled = false;
    });
  });

  function showMessage(text, type) {
    // Remove any existing messages
    const existingMessages = document.querySelectorAll('.message');
    existingMessages.forEach(msg => msg.remove());

    // Create new message element
    const message = document.createElement('div');
    message.className = `message ${type}`;
    message.textContent = text;
    message.setAttribute('role', 'alert');
    
    // Insert into message container
    const messageContainer = document.getElementById('message-container');
    if (messageContainer) {
      messageContainer.appendChild(message);
    }
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
      if (message.parentNode) {
        message.remove();
      }
    }, 5000);
  }
});
  