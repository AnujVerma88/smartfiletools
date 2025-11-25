/**
 * Mobile-Optimized File Upload Interface
 * Handles drag-and-drop, file selection, validation, and upload progress
 */

(function() {
    'use strict';

    // State management
    let selectedFile = null;
    let uploadInProgress = false;

    // DOM elements
    const elements = {
        uploadZone: document.getElementById('fileUploadZone'),
        fileInput: document.getElementById('fileInput'),
        fileSelected: document.getElementById('fileSelected'),
        fileName: document.getElementById('fileName'),
        fileSize: document.getElementById('fileSize'),
        fileIconType: document.getElementById('fileIconType'),
        fileRemoveBtn: document.getElementById('fileRemoveBtn'),
        uploadProgress: document.getElementById('uploadProgress'),
        uploadPercentage: document.getElementById('uploadPercentage'),
        uploadProgressBar: document.getElementById('uploadProgressBar'),
        uploadStatus: document.getElementById('uploadStatus'),
        uploadStatusText: document.getElementById('uploadStatusText'),
        fileUploadError: document.getElementById('fileUploadError'),
        fileUploadErrorText: document.getElementById('fileUploadErrorText'),
        convertBtn: document.getElementById('convertBtn')
    };

    // Configuration from data attributes
    const config = {
        maxSize: parseInt(elements.uploadZone?.dataset.maxSize || '50') * 1024 * 1024, // Convert MB to bytes
        acceptedFormats: elements.uploadZone?.dataset.acceptedFormats?.split(',') || []
    };

    // Prevent double initialization
    if (window.fileUploadInitialized) {
        return;
    }
    window.fileUploadInitialized = true;

    // Initialize when DOM is ready
    document.addEventListener('DOMContentLoaded', function() {
        if (!elements.uploadZone) return;
        
        initializeEventListeners();
        setupTouchSupport();
    });

    /**
     * Initialize all event listeners
     */
    function initializeEventListeners() {
        // File input change
        elements.fileInput?.addEventListener('change', handleFileSelect);

        // Browse button click (prevent bubbling to upload zone)
        const browseBtn = document.getElementById('browseFilesBtn');
        browseBtn?.addEventListener('click', function(e) {
            e.stopPropagation();
            elements.fileInput?.click();
        });

        // Upload zone click (only if not clicking on browse button)
        elements.uploadZone?.addEventListener('click', function(e) {
            // Don't trigger if clicking on the browse button
            if (e.target.closest('#browseFilesBtn')) {
                return;
            }
            elements.fileInput?.click();
        });

        // Drag and drop events
        elements.uploadZone?.addEventListener('dragover', handleDragOver);
        elements.uploadZone?.addEventListener('dragleave', handleDragLeave);
        elements.uploadZone?.addEventListener('drop', handleDrop);

        // Remove file button
        elements.fileRemoveBtn?.addEventListener('click', handleFileRemove);

        // Convert button
        elements.convertBtn?.addEventListener('click', handleConvert);

        // Prevent default drag behaviors on document
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            document.body.addEventListener(eventName, preventDefaults, false);
        });
    }

    /**
     * Setup touch-specific support for mobile devices
     */
    function setupTouchSupport() {
        if (!('ontouchstart' in window)) return;

        // Add touch feedback
        elements.uploadZone?.addEventListener('touchstart', function() {
            this.style.transform = 'scale(0.99)';
        });

        elements.uploadZone?.addEventListener('touchend', function() {
            this.style.transform = 'scale(1)';
        });

        // Optimize for mobile file picker
        if (elements.fileInput) {
            elements.fileInput.setAttribute('capture', 'environment');
        }
    }

    /**
     * Prevent default drag behaviors
     */
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    /**
     * Handle drag over event
     */
    function handleDragOver(e) {
        preventDefaults(e);
        this.classList.add('dragover');
    }

    /**
     * Handle drag leave event
     */
    function handleDragLeave(e) {
        preventDefaults(e);
        this.classList.remove('dragover');
    }

    /**
     * Handle file drop
     */
    function handleDrop(e) {
        preventDefaults(e);
        elements.uploadZone?.classList.remove('dragover');

        const files = e.dataTransfer?.files;
        if (files && files.length > 0) {
            handleFile(files[0]);
        }
    }

    /**
     * Handle file selection from input
     */
    function handleFileSelect(e) {
        const files = e.target.files;
        if (files && files.length > 0) {
            handleFile(files[0]);
        }
    }

    /**
     * Process selected file
     */
    function handleFile(file) {
        // Reset error state
        hideError();
        elements.uploadZone?.classList.remove('error');

        // Validate file
        const validation = validateFile(file);
        if (!validation.valid) {
            showError(validation.error);
            elements.uploadZone?.classList.add('error');
            return;
        }

        // Store file and update UI
        selectedFile = file;
        displaySelectedFile(file);
        
        // Enable convert button
        if (elements.convertBtn) {
            elements.convertBtn.style.display = 'flex';
            elements.convertBtn.disabled = false;
        }
    }

    /**
     * Validate file size and format
     */
    function validateFile(file) {
        // Check file size
        if (file.size > config.maxSize) {
            return {
                valid: false,
                error: `File size exceeds maximum limit of ${config.maxSize / (1024 * 1024)}MB`
            };
        }

        // Check file format
        const fileExtension = file.name.split('.').pop().toLowerCase();
        const isValidFormat = config.acceptedFormats.some(format => 
            format.toLowerCase().replace('.', '') === fileExtension
        );

        if (!isValidFormat && config.acceptedFormats.length > 0) {
            return {
                valid: false,
                error: `Invalid file format. Accepted formats: ${config.acceptedFormats.join(', ')}`
            };
        }

        return { valid: true };
    }

    /**
     * Display selected file information
     */
    function displaySelectedFile(file) {
        // Show file selected container
        if (elements.fileSelected) {
            elements.fileSelected.style.display = 'block';
        }

        // Update file name
        if (elements.fileName) {
            elements.fileName.textContent = file.name;
        }

        // Update file size
        if (elements.fileSize) {
            elements.fileSize.textContent = formatFileSize(file.size);
        }

        // Update file icon based on type
        if (elements.fileIconType) {
            const icon = getFileIcon(file.name);
            elements.fileIconType.className = icon;
        }

        // Hide upload zone (optional - can keep visible)
        // elements.uploadZone.style.display = 'none';
    }

    /**
     * Get appropriate icon for file type
     */
    function getFileIcon(filename) {
        const extension = filename.split('.').pop().toLowerCase();
        const iconMap = {
            'pdf': 'fas fa-file-pdf',
            'doc': 'fas fa-file-word',
            'docx': 'fas fa-file-word',
            'xls': 'fas fa-file-excel',
            'xlsx': 'fas fa-file-excel',
            'ppt': 'fas fa-file-powerpoint',
            'pptx': 'fas fa-file-powerpoint',
            'jpg': 'fas fa-file-image',
            'jpeg': 'fas fa-file-image',
            'png': 'fas fa-file-image',
            'gif': 'fas fa-file-image',
            'mp4': 'fas fa-file-video',
            'mov': 'fas fa-file-video',
            'avi': 'fas fa-file-video'
        };

        return iconMap[extension] || 'fas fa-file';
    }

    /**
     * Format file size for display
     */
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';

        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));

        return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
    }

    /**
     * Handle file removal
     */
    function handleFileRemove(e) {
        e.stopPropagation();

        // Reset state
        selectedFile = null;
        uploadInProgress = false;

        // Reset file input
        if (elements.fileInput) {
            elements.fileInput.value = '';
        }

        // Hide file selected container
        if (elements.fileSelected) {
            elements.fileSelected.style.display = 'none';
        }

        // Hide convert button
        if (elements.convertBtn) {
            elements.convertBtn.style.display = 'none';
            elements.convertBtn.disabled = true;
        }

        // Reset progress
        resetProgress();

        // Hide status
        if (elements.uploadStatus) {
            elements.uploadStatus.style.display = 'none';
        }

        // Clear error
        hideError();
        elements.uploadZone?.classList.remove('error');
    }

    /**
     * Handle convert button click
     */
    function handleConvert() {
        if (!selectedFile || uploadInProgress) return;

        uploadInProgress = true;
        elements.convertBtn.disabled = true;

        // Show progress
        if (elements.uploadProgress) {
            elements.uploadProgress.style.display = 'block';
        }

        // Hide previous status
        if (elements.uploadStatus) {
            elements.uploadStatus.style.display = 'none';
        }

        // Create form data
        const formData = new FormData();
        formData.append('file', selectedFile);
        formData.append('csrfmiddlewaretoken', getCsrfToken());

        // Upload file
        uploadFile(formData);
    }

    /**
     * Upload file with progress tracking
     */
    function uploadFile(formData) {
        const xhr = new XMLHttpRequest();

        // Track upload progress
        xhr.upload.addEventListener('progress', function(e) {
            if (e.lengthComputable) {
                const percentComplete = Math.round((e.loaded / e.total) * 100);
                updateProgress(percentComplete);
            }
        });

        // Handle completion
        xhr.addEventListener('load', function() {
            if (xhr.status === 200 || xhr.status === 302) {
                // Check if response is a redirect (HTML response)
                const contentType = xhr.getResponseHeader('Content-Type');
                
                // If it's HTML or a redirect, follow the redirect
                if (contentType && contentType.includes('text/html')) {
                    // Server returned HTML (likely a redirect page)
                    // Extract redirect URL from response or use responseURL
                    window.location.href = xhr.responseURL || window.location.href;
                    return;
                }
                
                // If responseURL changed, it means we were redirected
                if (xhr.responseURL && xhr.responseURL !== window.location.href) {
                    window.location.href = xhr.responseURL;
                    return;
                }
                
                // Try to parse JSON response
                try {
                    const response = JSON.parse(xhr.responseText);
                    handleUploadSuccess(response);
                } catch (e) {
                    // If JSON parsing fails but status is 200, assume success and redirect
                    console.log('Non-JSON response, following redirect...');
                    window.location.href = xhr.responseURL || window.location.href;
                }
            } else {
                handleUploadError('Upload failed. Please try again.');
            }
        });

        // Handle errors
        xhr.addEventListener('error', function() {
            handleUploadError('Network error. Please check your connection.');
        });

        xhr.addEventListener('abort', function() {
            handleUploadError('Upload cancelled.');
        });

        // Get tool slug from current URL path
        const pathParts = window.location.pathname.split('/').filter(p => p);
        const toolSlug = pathParts[pathParts.length - 1];
        const uploadUrl = `/tools/upload/${toolSlug}/`;

        // Send request
        xhr.open('POST', uploadUrl, true);
        xhr.send(formData);
    }

    /**
     * Update upload progress
     */
    function updateProgress(percentage) {
        if (elements.uploadPercentage) {
            elements.uploadPercentage.textContent = percentage + '%';
        }

        if (elements.uploadProgressBar) {
            elements.uploadProgressBar.style.width = percentage + '%';
        }
    }

    /**
     * Reset progress indicators
     */
    function resetProgress() {
        updateProgress(0);
        if (elements.uploadProgress) {
            elements.uploadProgress.style.display = 'none';
        }
    }

    /**
     * Handle successful upload
     */
    function handleUploadSuccess(response) {
        uploadInProgress = false;

        // Hide progress
        resetProgress();

        // Show success status
        if (elements.uploadStatus) {
            elements.uploadStatus.className = 'upload-status success';
            elements.uploadStatus.style.display = 'flex';
        }

        if (elements.uploadStatusText) {
            elements.uploadStatusText.textContent = 'File uploaded successfully!';
        }

        // Redirect to status page if provided
        if (response.redirect_url) {
            setTimeout(() => {
                window.location.href = response.redirect_url;
            }, 1000);
        } else if (response.conversion_id) {
            setTimeout(() => {
                window.location.href = `/tools/conversion/${response.conversion_id}/status/`;
            }, 1000);
        }
    }

    /**
     * Handle upload error
     */
    function handleUploadError(message) {
        uploadInProgress = false;

        // Hide progress
        resetProgress();

        // Show error status
        if (elements.uploadStatus) {
            elements.uploadStatus.className = 'upload-status error';
            elements.uploadStatus.style.display = 'flex';
        }

        if (elements.uploadStatusText) {
            elements.uploadStatusText.textContent = message;
        }

        // Re-enable convert button
        if (elements.convertBtn) {
            elements.convertBtn.disabled = false;
        }

        // Show error message
        showError(message);
    }

    /**
     * Show error message
     */
    function showError(message) {
        if (elements.fileUploadError) {
            elements.fileUploadError.style.display = 'flex';
        }

        if (elements.fileUploadErrorText) {
            elements.fileUploadErrorText.textContent = message;
        }
    }

    /**
     * Hide error message
     */
    function hideError() {
        if (elements.fileUploadError) {
            elements.fileUploadError.style.display = 'none';
        }
    }

    /**
     * Get CSRF token from cookie
     */
    function getCsrfToken() {
        const name = 'csrftoken';
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

    // Expose API for external use
    window.FileUpload = {
        reset: handleFileRemove,
        getSelectedFile: () => selectedFile,
        isUploading: () => uploadInProgress
    };

})();
