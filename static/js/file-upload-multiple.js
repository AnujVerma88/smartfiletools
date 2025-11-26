/**
 * Multi-File Upload Handler for PDF Merge
 * Handles drag-and-drop, file selection, reordering, and upload
 */

(function() {
    'use strict';

    // State
    let selectedFiles = [];
    let draggedIndex = null;

    // DOM Elements
    const uploadZone = document.getElementById('fileUploadZone');
    const fileInput = document.getElementById('fileInput');
    const browseBtn = document.getElementById('browseFilesBtn');
    const filesSelectedList = document.getElementById('filesSelectedList');
    const filesList = document.getElementById('filesList');
    const fileCount = document.getElementById('fileCount');
    const clearAllBtn = document.getElementById('clearAllBtn');
    const mergeBtn = document.getElementById('mergeBtn');
    const errorDiv = document.getElementById('fileUploadError');
    const errorText = document.getElementById('fileUploadErrorText');
    const progressContainer = document.getElementById('uploadProgressContainer');
    const progressBar = document.getElementById('uploadProgressBar');
    const progressPercentage = document.getElementById('uploadPercentage');
    const uploadStatus = document.getElementById('uploadStatus');
    const uploadStatusText = document.getElementById('uploadStatusText');

    // Configuration
    const maxSize = parseInt(uploadZone.dataset.maxSize) * 1024 * 1024; // Convert MB to bytes
    const acceptedFormats = uploadZone.dataset.acceptedFormats.split(',').map(f => f.trim());
    
    console.log('Accepted formats:', acceptedFormats);

    // Initialize
    function init() {
        setupEventListeners();
    }

    // Setup Event Listeners
    function setupEventListeners() {
        // Browse button
        browseBtn.addEventListener('click', () => fileInput.click());

        // File input change
        fileInput.addEventListener('change', handleFileSelect);

        // Drag and drop
        uploadZone.addEventListener('dragover', handleDragOver);
        uploadZone.addEventListener('dragleave', handleDragLeave);
        uploadZone.addEventListener('drop', handleDrop);

        // Clear all button
        clearAllBtn.addEventListener('click', clearAllFiles);

        // Merge button
        mergeBtn.addEventListener('click', handleMerge);
    }

    // Handle file selection
    function handleFileSelect(e) {
        const files = Array.from(e.target.files);
        addFiles(files);
        fileInput.value = ''; // Reset input
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
        
        const files = Array.from(e.dataTransfer.files);
        addFiles(files);
    }

    // Add files to the list
    function addFiles(files) {
        hideError();
        
        for (const file of files) {
            // Validate file
            const validation = validateFile(file);
            if (!validation.valid) {
                showError(validation.error);
                continue;
            }

            // Check for duplicates
            const isDuplicate = selectedFiles.some(f => 
                f.name === file.name && f.size === file.size
            );
            
            if (isDuplicate) {
                showError(`File "${file.name}" is already added`);
                continue;
            }

            // Add to selected files
            selectedFiles.push(file);
        }

        updateFilesList();
        updateUI();
    }

    // Validate file
    function validateFile(file) {
        // Check file type
        const fileExt = file.name.split('.').pop().toLowerCase();
        const fileExtWithDot = '.' + fileExt;
        
        // Check if format is accepted (with or without dot)
        const isAccepted = acceptedFormats.some(format => {
            const normalizedFormat = format.toLowerCase().trim();
            return normalizedFormat === fileExt || 
                   normalizedFormat === fileExtWithDot ||
                   normalizedFormat === `.${fileExt}`;
        });
        
        if (!isAccepted) {
            return {
                valid: false,
                error: `Invalid file type. Only ${acceptedFormats.join(', ')} files are allowed.`
            };
        }

        // Check file size
        if (file.size > maxSize) {
            const maxSizeMB = maxSize / (1024 * 1024);
            return {
                valid: false,
                error: `File "${file.name}" is too large. Maximum size is ${maxSizeMB}MB.`
            };
        }

        return { valid: true };
    }

    // Update files list display
    function updateFilesList() {
        filesList.innerHTML = '';

        selectedFiles.forEach((file, index) => {
            const fileItem = createFileItem(file, index);
            filesList.appendChild(fileItem);
        });
    }

    // Create file item element
    function createFileItem(file, index) {
        const div = document.createElement('div');
        div.className = 'file-item';
        div.draggable = true;
        div.dataset.index = index;

        div.innerHTML = `
            <div class="file-item-drag-handle">
                <i class="fas fa-grip-vertical"></i>
            </div>
            <div class="file-item-icon">
                <i class="fas fa-file-pdf"></i>
            </div>
            <div class="file-item-details">
                <div class="file-item-name">${escapeHtml(file.name)}</div>
                <div class="file-item-size">${formatFileSize(file.size)}</div>
            </div>
            <button type="button" class="file-item-remove" data-index="${index}">
                <i class="fas fa-times"></i>
            </button>
        `;

        // Remove button
        const removeBtn = div.querySelector('.file-item-remove');
        removeBtn.addEventListener('click', () => removeFile(index));

        // Drag events
        div.addEventListener('dragstart', handleFileDragStart);
        div.addEventListener('dragover', handleFileDragOver);
        div.addEventListener('drop', handleFileDrop);
        div.addEventListener('dragend', handleFileDragEnd);

        return div;
    }

    // File drag and drop for reordering
    function handleFileDragStart(e) {
        draggedIndex = parseInt(e.currentTarget.dataset.index);
        e.currentTarget.classList.add('dragging');
    }

    function handleFileDragOver(e) {
        e.preventDefault();
    }

    function handleFileDrop(e) {
        e.preventDefault();
        const dropIndex = parseInt(e.currentTarget.dataset.index);
        
        if (draggedIndex !== null && draggedIndex !== dropIndex) {
            // Reorder files
            const draggedFile = selectedFiles[draggedIndex];
            selectedFiles.splice(draggedIndex, 1);
            selectedFiles.splice(dropIndex, 0, draggedFile);
            
            updateFilesList();
        }
    }

    function handleFileDragEnd(e) {
        e.currentTarget.classList.remove('dragging');
        draggedIndex = null;
    }

    // Remove file
    function removeFile(index) {
        selectedFiles.splice(index, 1);
        updateFilesList();
        updateUI();
    }

    // Clear all files
    function clearAllFiles() {
        selectedFiles = [];
        updateFilesList();
        updateUI();
        hideSuccess();
    }

    // Update UI state
    function updateUI() {
        const hasFiles = selectedFiles.length > 0;
        const canMerge = selectedFiles.length >= 2;

        // Show/hide files list
        filesSelectedList.style.display = hasFiles ? 'block' : 'none';
        
        // Update file count
        fileCount.textContent = selectedFiles.length;

        // Show/hide merge button
        mergeBtn.style.display = hasFiles ? 'block' : 'none';
        mergeBtn.disabled = !canMerge;

        // Update button text
        if (canMerge) {
            mergeBtn.querySelector('span').textContent = `Merge ${selectedFiles.length} PDFs`;
        } else if (hasFiles) {
            mergeBtn.querySelector('span').textContent = 'Add at least 2 files to merge';
        }
    }

    // Handle merge
    async function handleMerge() {
        if (selectedFiles.length < 2) {
            showError('Please select at least 2 PDF files to merge');
            return;
        }

        hideError();
        hideSuccess();
        
        // Disable button
        mergeBtn.disabled = true;
        mergeBtn.querySelector('span').textContent = 'Merging...';

        // Show progress
        progressContainer.style.display = 'block';
        updateProgress(0);

        try {
            // Create FormData
            const formData = new FormData();
            selectedFiles.forEach((file, index) => {
                formData.append('files', file);
            });

            // Get CSRF token
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
                             getCookie('csrftoken');
            
            // Upload files
            const response = await fetch('/api/v1/convert/merge-pdf/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                },
                body: formData,
            });

            if (!response.ok) {
                const errorData = await response.json();
                console.error('Merge error response:', errorData);
                throw new Error(errorData.message || errorData.error || 'Merge failed');
            }

            const result = await response.json();
            console.log('Merge success:', result);
            updateProgress(100);

            // Show success with download button
            setTimeout(() => {
                progressContainer.style.display = 'none';
                showSuccess('PDFs merged successfully!', result.data.download_url);
                
                // Hide merge button
                mergeBtn.style.display = 'none';
            }, 500);

        } catch (error) {
            console.error('Merge error:', error);
            progressContainer.style.display = 'none';
            showError(error.message || 'Failed to merge PDFs. Please try again.');
            mergeBtn.disabled = false;
            mergeBtn.querySelector('span').textContent = `Merge ${selectedFiles.length} PDFs`;
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
        
        // Auto-hide after 5 seconds
        setTimeout(hideError, 5000);
    }

    // Hide error
    function hideError() {
        errorDiv.style.display = 'none';
    }

    // Show success
    function showSuccess(message, downloadUrl) {
        uploadStatusText.innerHTML = message;
        
        // Add download button if URL provided
        if (downloadUrl) {
            const downloadBtn = document.createElement('a');
            downloadBtn.href = downloadUrl;
            downloadBtn.className = 'download-btn';
            downloadBtn.style.cssText = 'display: inline-block; margin-top: 1rem; padding: 0.75rem 1.5rem; background: #14B8A6; color: white; text-decoration: none; border-radius: 8px; font-weight: 600; transition: all 0.3s;';
            downloadBtn.innerHTML = '<i class="fas fa-download"></i> Download Merged PDF';
            downloadBtn.onmouseover = function() { this.style.background = '#0F766E'; };
            downloadBtn.onmouseout = function() { this.style.background = '#14B8A6'; };
            
            // Add "Start New Merge" button
            const newMergeBtn = document.createElement('button');
            newMergeBtn.type = 'button';
            newMergeBtn.className = 'new-merge-btn';
            newMergeBtn.style.cssText = 'display: inline-block; margin-top: 1rem; margin-left: 1rem; padding: 0.75rem 1.5rem; background: white; color: #14B8A6; border: 2px solid #14B8A6; text-decoration: none; border-radius: 8px; font-weight: 600; cursor: pointer; transition: all 0.3s;';
            newMergeBtn.innerHTML = '<i class="fas fa-plus"></i> Start New Merge';
            newMergeBtn.onclick = function() {
                clearAllFiles();
                hideSuccess();
                mergeBtn.style.display = 'block';
            };
            newMergeBtn.onmouseover = function() { this.style.background = '#F0FDFA'; };
            newMergeBtn.onmouseout = function() { this.style.background = 'white'; };
            
            uploadStatusText.appendChild(document.createElement('br'));
            uploadStatusText.appendChild(downloadBtn);
            uploadStatusText.appendChild(newMergeBtn);
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

    // Utility: Escape HTML
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
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
