/**
 * Split PDF Upload Handler with Page Selection
 * Renders PDF pages and allows user to select which pages to extract
 */

(function() {
    'use strict';

    // State
    let selectedFile = null;
    let pdfDoc = null;
    let selectedPages = new Set();

    // DOM Elements
    const uploadZone = document.getElementById('fileUploadZone');
    const fileInput = document.getElementById('fileInput');
    const browseBtn = document.getElementById('browseFilesBtn');
    const fileSelected = document.getElementById('fileSelected');
    const fileName = document.getElementById('fileName');
    const fileSize = document.getElementById('fileSize');
    const filePages = document.getElementById('filePages');
    const fileRemoveBtn = document.getElementById('fileRemoveBtn');
    const pageSelection = document.getElementById('pageSelection');
    const pageGrid = document.getElementById('pageGrid');
    const selectAllBtn = document.getElementById('selectAllBtn');
    const deselectAllBtn = document.getElementById('deselectAllBtn');
    const selectedCount = document.getElementById('selectedCount');
    const extractBtn = document.getElementById('extractBtn');
    const errorDiv = document.getElementById('fileUploadError');
    const errorText = document.getElementById('fileUploadErrorText');
    const progressContainer = document.getElementById('uploadProgressContainer');
    const progressBar = document.getElementById('uploadProgressBar');
    const progressPercentage = document.getElementById('uploadPercentage');
    const uploadStatus = document.getElementById('uploadStatus');
    const uploadStatusText = document.getElementById('uploadStatusText');

    // Configuration
    const maxSize = parseInt(uploadZone.dataset.maxSize) * 1024 * 1024;

    // Initialize
    function init() {
        setupEventListeners();
    }

    // Setup Event Listeners
    function setupEventListeners() {
        browseBtn.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', handleFileSelect);
        uploadZone.addEventListener('dragover', handleDragOver);
        uploadZone.addEventListener('dragleave', handleDragLeave);
        uploadZone.addEventListener('drop', handleDrop);
        fileRemoveBtn.addEventListener('click', removeFile);
        selectAllBtn.addEventListener('click', selectAllPages);
        deselectAllBtn.addEventListener('click', deselectAllPages);
        extractBtn.addEventListener('click', handleExtract);
    }

    // Handle file selection
    function handleFileSelect(e) {
        const file = e.target.files[0];
        if (file) {
            addFile(file);
        }
        fileInput.value = '';
    }

    // Handle drag over
    function handleDragOver(e) {
        e.preventDefault();
        uploadZone.classList.add('drag-over');
    }

    // Handle drag leave
    function handleDragLeave(e) {
        e.preventDefault();
        uploadZone.classList.remove('drag-over');
    }

    // Handle drop
    function handleDrop(e) {
        e.preventDefault();
        uploadZone.classList.remove('drag-over');
        
        const file = e.dataTransfer.files[0];
        if (file) {
            addFile(file);
        }
    }

    // Add file
    async function addFile(file) {
        hideError();
        
        // Validate file
        const validation = validateFile(file);
        if (!validation.valid) {
            showError(validation.error);
            return;
        }

        selectedFile = file;
        selectedPages.clear();
        updateFileDisplay();
        
        // Load and render PDF pages
        await loadPDF(file);
    }

    // Validate file
    function validateFile(file) {
        if (!file.name.toLowerCase().endsWith('.pdf')) {
            return {
                valid: false,
                error: 'Invalid file type. Only PDF files are allowed.'
            };
        }

        if (file.size > maxSize) {
            const maxSizeMB = maxSize / (1024 * 1024);
            return {
                valid: false,
                error: `File is too large. Maximum size is ${maxSizeMB}MB.`
            };
        }

        return { valid: true };
    }

    // Update file display
    function updateFileDisplay() {
        fileName.textContent = selectedFile.name;
        fileSize.textContent = formatFileSize(selectedFile.size);
        filePages.textContent = 'Loading pages...';
        fileSelected.style.display = 'block';
    }

    // Load PDF
    async function loadPDF(file) {
        try {
            const arrayBuffer = await file.arrayBuffer();
            pdfDoc = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
            
            filePages.textContent = `${pdfDoc.numPages} pages`;
            
            // Show page selection
            pageSelection.style.display = 'block';
            
            // Render all pages
            await renderAllPages();
            
            updateUI();
        } catch (error) {
            console.error('Error loading PDF:', error);
            showError('Failed to load PDF. Please try another file.');
        }
    }

    // Render all pages
    async function renderAllPages() {
        pageGrid.innerHTML = '';
        
        for (let pageNum = 1; pageNum <= pdfDoc.numPages; pageNum++) {
            const pageItem = await renderPage(pageNum);
            pageGrid.appendChild(pageItem);
        }
    }

    // Render single page
    async function renderPage(pageNum) {
        const page = await pdfDoc.getPage(pageNum);
        
        // Create canvas
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        
        // Set scale for thumbnail
        const viewport = page.getViewport({ scale: 0.5 });
        canvas.width = viewport.width;
        canvas.height = viewport.height;
        
        // Render page
        await page.render({
            canvasContext: context,
            viewport: viewport
        }).promise;
        
        // Create page item
        const pageItem = document.createElement('div');
        pageItem.className = 'page-item';
        pageItem.dataset.page = pageNum;
        
        pageItem.innerHTML = `
            <img src="${canvas.toDataURL()}" class="page-thumbnail" alt="Page ${pageNum}">
            <div class="page-number">Page ${pageNum}</div>
        `;
        
        // Add click handler
        pageItem.addEventListener('click', () => togglePage(pageNum));
        
        return pageItem;
    }

    // Toggle page selection
    function togglePage(pageNum) {
        if (selectedPages.has(pageNum)) {
            selectedPages.delete(pageNum);
        } else {
            selectedPages.add(pageNum);
        }
        
        updatePageSelection();
        updateUI();
    }

    // Select all pages
    function selectAllPages() {
        selectedPages.clear();
        for (let i = 1; i <= pdfDoc.numPages; i++) {
            selectedPages.add(i);
        }
        updatePageSelection();
        updateUI();
    }

    // Deselect all pages
    function deselectAllPages() {
        selectedPages.clear();
        updatePageSelection();
        updateUI();
    }

    // Update page selection UI
    function updatePageSelection() {
        document.querySelectorAll('.page-item').forEach(item => {
            const pageNum = parseInt(item.dataset.page);
            if (selectedPages.has(pageNum)) {
                item.classList.add('selected');
            } else {
                item.classList.remove('selected');
            }
        });
        
        selectedCount.textContent = selectedPages.size;
    }

    // Remove file
    function removeFile() {
        selectedFile = null;
        pdfDoc = null;
        selectedPages.clear();
        fileSelected.style.display = 'none';
        pageSelection.style.display = 'none';
        pageGrid.innerHTML = '';
        updateUI();
        hideSuccess();
    }

    // Update UI state
    function updateUI() {
        const hasFile = selectedFile !== null;
        const hasSelection = selectedPages.size > 0;

        extractBtn.style.display = hasFile ? 'block' : 'none';
        extractBtn.disabled = !hasSelection;
        
        if (hasSelection) {
            extractBtn.querySelector('span').textContent = `Extract ${selectedPages.size} Page${selectedPages.size > 1 ? 's' : ''}`;
        } else {
            extractBtn.querySelector('span').textContent = 'Select pages to extract';
        }
    }

    // Handle extract
    async function handleExtract() {
        if (!selectedFile || selectedPages.size === 0) {
            showError('Please select at least one page');
            return;
        }

        hideError();
        hideSuccess();
        
        extractBtn.disabled = true;
        extractBtn.querySelector('span').textContent = 'Extracting...';

        progressContainer.style.display = 'block';
        updateProgress(0);

        try {
            const formData = new FormData();
            formData.append('file', selectedFile);
            
            // Convert selected pages to array and sort
            const pagesArray = Array.from(selectedPages).sort((a, b) => a - b);
            formData.append('page_ranges', JSON.stringify([[pagesArray[0], pagesArray[pagesArray.length - 1]]]));
            formData.append('selected_pages', JSON.stringify(pagesArray));
            formData.append('split_mode', 'custom');

            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
                             getCookie('csrftoken');
            
            const response = await fetch('/api/v1/convert/split-pdf/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                },
                body: formData,
            });

            if (!response.ok) {
                const errorData = await response.json();
                console.error('Extract error response:', errorData);
                throw new Error(errorData.message || errorData.error || 'Extract failed');
            }

            const result = await response.json();
            console.log('Extract success:', result);
            updateProgress(100);

            setTimeout(() => {
                progressContainer.style.display = 'none';
                showSuccess(`Successfully extracted ${selectedPages.size} page${selectedPages.size > 1 ? 's' : ''}!`, result.data?.conversion_id);
                extractBtn.style.display = 'none';
            }, 500);

        } catch (error) {
            console.error('Extract error:', error);
            progressContainer.style.display = 'none';
            showError(error.message || 'Failed to extract pages. Please try again.');
            extractBtn.disabled = false;
            updateUI();
        }
    }

    // Update progress
    function updateProgress(percent) {
        progressBar.style.width = percent + '%';
        progressPercentage.textContent = Math.round(percent) + '%';
    }

    // Show error
    function showError(message) {
        errorText.textContent = message;
        errorDiv.style.display = 'block';
        setTimeout(hideError, 5000);
    }

    // Hide error
    function hideError() {
        errorDiv.style.display = 'none';
    }

    // Show success
    function showSuccess(message, conversionId) {
        uploadStatusText.innerHTML = message;
        
        if (conversionId) {
            const viewBtn = document.createElement('a');
            viewBtn.href = '/dashboard/';
            viewBtn.className = 'download-btn';
            viewBtn.style.cssText = 'display: inline-block; margin-top: 1rem; padding: 0.75rem 1.5rem; background: #14B8A6; color: white; text-decoration: none; border-radius: 8px; font-weight: 600; transition: all 0.3s;';
            viewBtn.innerHTML = '<i class="fas fa-folder-open"></i> View in Dashboard';
            viewBtn.onmouseover = function() { this.style.background = '#0F766E'; };
            viewBtn.onmouseout = function() { this.style.background = '#14B8A6'; };
            
            const newBtn = document.createElement('button');
            newBtn.type = 'button';
            newBtn.style.cssText = 'display: inline-block; margin-top: 1rem; margin-left: 1rem; padding: 0.75rem 1.5rem; background: white; color: #14B8A6; border: 2px solid #14B8A6; border-radius: 8px; font-weight: 600; cursor: pointer; transition: all 0.3s;';
            newBtn.innerHTML = '<i class="fas fa-plus"></i> Extract from Another PDF';
            newBtn.onclick = function() {
                removeFile();
                hideSuccess();
                extractBtn.style.display = 'block';
            };
            newBtn.onmouseover = function() { this.style.background = '#F0FDFA'; };
            newBtn.onmouseout = function() { this.style.background = 'white'; };
            
            uploadStatusText.appendChild(document.createElement('br'));
            uploadStatusText.appendChild(viewBtn);
            uploadStatusText.appendChild(newBtn);
        }
        
        uploadStatus.style.display = 'block';
    }

    // Hide success
    function hideSuccess() {
        uploadStatus.style.display = 'none';
        uploadStatusText.innerHTML = '';
    }

    // Utility: Format file size
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }

    // Utility: Get cookie
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
