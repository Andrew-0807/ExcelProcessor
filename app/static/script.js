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

  // Assign stagger index to each mode card for CSS animation-delay
  document.querySelectorAll('.mode-card').forEach((card, i) => {
    card.style.setProperty('--index', i);
  });

  // Show the 'Nr. inreg.' start field for the modes that fill it (CardCec, SGR, RetuRO).
  function toggleCardcecOptions() {
    const opts = document.getElementById('cardcec-options');
    if (!opts) return;
    const selected = document.querySelector('input[name="process_type"]:checked');
    opts.hidden = !(selected && (selected.value === 'cardcec' || selected.value === 'sgr' || selected.value === 'returo'));
  }
  document.querySelectorAll('input[name="process_type"]').forEach(r =>
    r.addEventListener('change', toggleCardcecOptions));
  toggleCardcecOptions();

  // Track whether the user has explicitly chosen a process type.
  // We listen on the label cards (not just the hidden radio inputs) because
  // clicking a <label> doesn't always fire a reliable 'change' on the radio.
  let userSelectedProcessType = false;
  document.querySelectorAll('.mode-card').forEach(card => {
    card.addEventListener('click', () => {
      userSelectedProcessType = true;
    });
  });

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

  // Update file input change handler.
  // Reset the manual-selection flag when the user picks a completely new set of
  // files so the auto-suggest fires on the first drop/select, but only then.
  fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) {
      userSelectedProcessType = false;
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

  // ── Report-a-problem modal ──
  const reportBtn = document.getElementById('reportBtn');
  const reportModal = document.getElementById('report-modal');
  if (reportBtn && reportModal) {
    const reportDescription = document.getElementById('reportDescription');
    const reportFileInput = document.getElementById('reportFileInput');
    const reportFileHint = document.getElementById('reportFileHint');
    const reportSubmitBtn = document.getElementById('reportSubmitBtn');
    const reportMessage = document.getElementById('report-message');
    const reportCloseBtn = reportModal.querySelector('.report-modal-close');
    const reportOverlay = reportModal.querySelector('.modal-overlay');

    function setReportMessage(text, type) {
      reportMessage.textContent = text || '';
      reportMessage.className = 'report-message' + (type ? ' ' + type : '');
    }

    function updateReportHint() {
      const count = reportFileInput.files.length;
      if (count === 1) {
        reportFileHint.textContent = `Atașat: ${reportFileInput.files[0].name}`;
      } else if (count > 1) {
        reportFileHint.textContent = `${count} fișiere atașate`;
      } else {
        reportFileHint.textContent = 'Poți atașa fișierul care a cauzat eroarea.';
      }
    }

    function openReportModal() {
      setReportMessage('');
      // Pre-attach whatever the user already selected in the main drop area so
      // "send the file with the error" needs no extra clicks.
      if (fileInput.files && fileInput.files.length) {
        const dt = new DataTransfer();
        Array.from(fileInput.files).forEach(f => dt.items.add(f));
        reportFileInput.files = dt.files;
      }
      updateReportHint();
      reportModal.classList.add('show');
      reportModal.setAttribute('aria-hidden', 'false');
    }

    function closeReportModal() {
      reportModal.classList.remove('show');
      reportModal.setAttribute('aria-hidden', 'true');
    }

    reportBtn.addEventListener('click', openReportModal);
    if (reportCloseBtn) reportCloseBtn.addEventListener('click', closeReportModal);
    if (reportOverlay) reportOverlay.addEventListener('click', closeReportModal);
    reportFileInput.addEventListener('change', updateReportHint);

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && reportModal.classList.contains('show')) {
        closeReportModal();
      }
    });

    reportSubmitBtn.addEventListener('click', () => {
      const description = reportDescription.value.trim();
      if (!description && reportFileInput.files.length === 0) {
        setReportMessage('Adaugă o descriere sau atașează un fișier.', 'error');
        return;
      }

      const formData = new FormData();
      formData.append('description', description);
      const selectedType = document.querySelector('input[name="process_type"]:checked');
      if (selectedType) formData.append('process_type', selectedType.value);
      Array.from(reportFileInput.files).forEach(f => formData.append('file', f));

      reportSubmitBtn.disabled = true;
      setReportMessage('Se trimite...', '');

      fetch('/report-problem', { method: 'POST', body: formData })
        .then(response => response.json().then(data => ({ ok: response.ok, data })))
        .then(({ ok, data }) => {
          if (!ok) throw new Error((data && data.message) || 'Trimiterea a eșuat.');
          setReportMessage((data && data.message) || 'Raportul a fost trimis. Mulțumim!', 'success');
          reportDescription.value = '';
          reportFileInput.value = '';
          updateReportHint();
          setTimeout(closeReportModal, 1800);
        })
        .catch(err => {
          console.error('[ExcelProcessor] Report failed:', err);
          setReportMessage(err.message || 'Ceva nu a funcționat. Încearcă din nou.', 'error');
        })
        .finally(() => {
          reportSubmitBtn.disabled = false;
        });
    });
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
    userSelectedProcessType = false;  // new batch of files — allow auto-suggest once
    updateDropAreaText(files.length);
    displayFileList(files);
  }

  function updateDropAreaText(fileCount) {
    const mainText = dropArea.querySelector('.main-text');
    const subText = dropArea.querySelector('.sub-text');
    
    if (fileCount === 1) {
      mainText.textContent = `1 fișier selectat - Gata de procesare!`;
      subText.textContent = 'Click pentru a adăuga mai multe fișiere sau a schimba selecția';
    } else if (fileCount > 1) {
      mainText.textContent = `${fileCount} fișiere selectate - Gata de procesare!`;
      subText.textContent = 'Click pentru a adăuga mai multe fișiere sau a schimba selecția';
    } else {
      mainText.textContent = 'Trage și plasează fișierele aici';
      subText.textContent = 'sau click pentru a selecta';
    }
  }

  function displayFileList(files) {
    if (!fileList) return;
    
    fileList.innerHTML = '';

    if (files.length === 0) {
      const emptyMsg = document.createElement('p');
      emptyMsg.className = 'file-list-empty';
      emptyMsg.textContent = 'Niciun fișier selectat';
      fileList.appendChild(emptyMsg);
      return;
    }
    
    // Auto-match process type based on first file name, but only if the user
    // hasn't already made a manual selection.
    if (files.length > 0 && !userSelectedProcessType) {
      const fileName = files[0].name.toLowerCase();
      let processType = null;

      if (fileName.includes('borderou')) {
        processType = 'borderou';
      } else if (fileName.includes('pos') || fileName.includes('incasari')) {
        processType = 'cardcec';
      } else if (fileName.includes('aviz')) {
        processType = 'avize';
      }

      if (processType) {
        const radio = document.querySelector(`input[name="process_type"][value="${processType}"]`);
        if (radio) {
          radio.checked = true;
        }
      }
      toggleCardcecOptions();
    }
    
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
    
    if (!files.length) {
      showMessage('Te rog selectează un fișier.', 'error');
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
    if (processType === 'cardcec' || processType === 'sgr' || processType === 'returo') {
      const startNr = document.getElementById('startNrInput').value.trim();
      if (startNr) formData.append('start_nr', startNr);
    }

    // Per-file errors from a partially successful run, shown to the user after
    // the download completes.
    let partialErrors = [];

    fetch('/process', {
      method: 'POST',
      body: formData
    })
    .then(response => {
      // Check for partial-success warnings in header
      const warnings = response.headers.get('X-Processing-Warnings');
      if (warnings) {
        try {
          const warningList = JSON.parse(warnings);
          partialErrors = warningList;
          console.warn('%c[ExcelProcessor] Some files had errors:', 'color: orange; font-weight: bold;');
          warningList.forEach(w => {
            console.warn(`  File: ${w.file} — Error: ${w.error}`);
          });
        } catch (e) {
          console.warn('[ExcelProcessor] Processing warnings:', warnings);
        }
      }

      if (!response.ok) {
        // Try to read the error body as JSON for debug info
        const contentType = response.headers.get('content-type') || '';
        if (contentType.includes('application/json')) {
          return response.json().then(errData => {
            console.error('%c[ExcelProcessor] Processing FAILED', 'color: red; font-weight: bold;');
            console.error('Status:', response.status, response.statusText);
            console.error('Message:', errData.message);
            if (errData.errors) {
              errData.errors.forEach((err, i) => {
                console.group(`Error ${i + 1}: ${err.file}`);
                console.error('Error:', err.error);
                if (err.traceback) {
                  console.error('Traceback:\n' + err.traceback);
                }
                console.groupEnd();
              });
            }
            const uiError = new Error(errData.message || 'Processing failed');
            // Only file + error reach the UI; the traceback stays in the console.
            uiError.details = (errData.errors || []).map(e => ({
              file: e.file,
              error: e.error
            }));
            throw uiError;
          });
        } else {
          return response.text().then(text => {
            console.error('%c[ExcelProcessor] Processing FAILED', 'color: red; font-weight: bold;');
            console.error('Status:', response.status, response.statusText);
            console.error('Response:', text);
            const uiError = new Error(text || 'Processing failed');
            uiError.details = [];
            throw uiError;
          });
        }
      }
      
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
      
      // Show success message — or, if some files failed, the per-file reasons.
      if (partialErrors.length) {
        showMessage(
          'Fișierele valide au fost descărcate, dar unele nu au putut fi procesate:',
          'error',
          partialErrors
        );
      } else {
        showMessage('Fișiere procesate cu succes!', 'success');
      }
    })
    .catch(err => {
      console.error('[ExcelProcessor] Error:', err);
      // err.details is only set for responses that came back from the server,
      // so network/JS failures still fall back to the generic wording.
      const fromServer = Array.isArray(err.details);
      const text = fromServer && err.message && !err.message.trim().startsWith('<')
        ? err.message
        : 'Ceva nu a funcționat. Încearcă din nou.';
      showMessage(text, 'error', fromServer ? err.details : []);
    })
    .finally(() => {
      // Reset button state
      processBtn.classList.remove('loading');
      processBtn.innerHTML = originalContent;
      processBtn.disabled = false;
    });
  });

  // `details` is an optional array of { file, error } coming from the backend.
  // Each entry is rendered verbatim under the main text, prefixed by its filename.
  function showMessage(text, type, details) {
    // Remove any existing messages
    const existingMessages = document.querySelectorAll('.message');
    existingMessages.forEach(msg => msg.remove());

    // Create new message element
    const message = document.createElement('div');
    message.className = `message ${type}`;
    message.setAttribute('role', 'alert');

    const body = document.createElement('div');
    body.className = 'message-body';

    const main = document.createElement('span');
    main.textContent = text;
    body.appendChild(main);

    const list = Array.isArray(details) ? details : [];
    list.forEach(d => {
      const detail = document.createElement('span');
      detail.className = 'message-detail';

      const fileName = document.createElement('strong');
      fileName.className = 'message-detail-file';
      fileName.textContent = d.file || 'Fișier necunoscut';
      detail.appendChild(fileName);

      // Backend message kept verbatim (Romanian, user-facing). No traceback here.
      detail.appendChild(document.createTextNode(d.error || ''));
      body.appendChild(detail);
    });

    message.appendChild(body);

    // Insert into message container
    const messageContainer = document.getElementById('message-container');
    if (messageContainer) {
      messageContainer.appendChild(message);
    }

    // Auto-remove with fade-out. Detailed errors stay longer so they can be read.
    setTimeout(() => {
      if (message.parentNode) {
        message.style.opacity = '0';
        message.style.transform = 'translateY(6px)';
        setTimeout(() => message.parentNode && message.remove(), 260);
      }
    }, list.length ? 20000 : 5000);
  }
});
  