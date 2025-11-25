/**
 * Conversion Status Polling
 * Polls the server for conversion status updates and displays progress
 */

(function() {
    'use strict';

    // Configuration
    const POLL_INTERVAL = 2000; // 2 seconds
    const MAX_POLL_ATTEMPTS = 150; // 5 minutes max (150 * 2 seconds)
    
    // State
    let pollCount = 0;
    let pollTimer = null;
    let conversionId = null;

    // DOM elements
    const elements = {
        statusContainer: document.getElementById('conversionStatus'),
        statusText: document.getElementById('statusText'),
        statusIcon: document.getElementById('statusIcon'),
        progressBar: document.getElementById('progressBar'),
        progressPercentage: document.getElementById('progressPercentage'),
        downloadBtn: document.getElementById('downloadBtn'),
        dashboardBtn: document.getElementById('dashboardBtn'),
        errorMessage: document.getElementById('errorMessage'),
        processingTime: document.getElementById('processingTime'),
        fileSizeBefore: document.getElementById('fileSizeBefore'),
        fileSizeAfter: document.getElementById('fileSizeAfter'),
        compressionRatio: document.getElementById('compressionRatio')
    };

    // Initialize when DOM is ready
    document.addEventListener('DOMContentLoaded', function() {
        // Get conversion ID from data attribute or URL
        const statusContainer = elements.statusContainer;
        if (statusContainer) {
            conversionId = statusContainer.dataset.conversionId;
            if (conversionId) {
                startPolling();
            }
        }
    });

    /**
     * Start polling for status updates
     */
    function startPolling() {
        pollStatus();
        pollTimer = setInterval(pollStatus, POLL_INTERVAL);
    }

    /**
     * Stop polling
     */
    function stopPolling() {
        if (pollTimer) {
            clearInterval(pollTimer);
            pollTimer = null;
        }
    }

    /**
     * Poll server for conversion status
     */
    function pollStatus() {
        pollCount++;

        // Stop polling after max attempts
        if (pollCount > MAX_POLL_ATTEMPTS) {
            stopPolling();
            showError('Conversion is taking longer than expected. Please refresh the page.');
            return;
        }

        // Make AJAX request
        fetch(`/tools/conversion/${conversionId}/status/api/`, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            handleStatusUpdate(data);
        })
        .catch(error => {
            console.error('Error polling status:', error);
            // Don't stop polling on network errors, just log them
        });
    }

    /**
     * Handle status update from server
     */
    function handleStatusUpdate(data) {
        const status = data.status;

        switch(status) {
            case 'pending':
                updateStatus('Pending', 'fas fa-clock', 'info', 10);
                break;

            case 'processing':
                updateStatus('Processing', 'fas fa-spinner fa-spin', 'info', 50);
                break;

            case 'completed':
                stopPolling();
                updateStatus('Completed', 'fas fa-check-circle', 'success', 100);
                showCompletedInfo(data);
                break;

            case 'failed':
                stopPolling();
                updateStatus('Failed', 'fas fa-times-circle', 'error', 0);
                showError(data.error_message || 'Conversion failed. Please try again.');
                break;

            default:
                updateStatus('Unknown', 'fas fa-question-circle', 'warning', 0);
        }
    }

    /**
     * Update status display
     */
    function updateStatus(text, icon, type, progress) {
        // Update status text
        if (elements.statusText) {
            elements.statusText.textContent = text;
        }

        // Update status icon
        if (elements.statusIcon) {
            elements.statusIcon.className = icon;
        }

        // Update status container class
        if (elements.statusContainer) {
            elements.statusContainer.className = `conversion-status status-${type}`;
        }

        // Update progress bar
        if (elements.progressBar) {
            elements.progressBar.style.width = progress + '%';
        }

        if (elements.progressPercentage) {
            elements.progressPercentage.textContent = progress + '%';
        }
    }

    /**
     * Show completed conversion information
     */
    function showCompletedInfo(data) {
        // Show download button
        if (elements.downloadBtn && data.download_url) {
            elements.downloadBtn.href = data.download_url;
            elements.downloadBtn.style.display = 'inline-flex';
        }
        
        // Change dashboard button to green success style
        if (elements.dashboardBtn) {
            elements.dashboardBtn.className = 'btn-success';
            elements.dashboardBtn.innerHTML = '<i class="fas fa-check-circle"></i>&nbsp; Back to Dashboard';
        }

        // Show processing time
        if (elements.processingTime && data.processing_time) {
            elements.processingTime.textContent = data.processing_time.toFixed(2) + 's';
        }

        // Show file sizes
        if (elements.fileSizeBefore && data.file_size_before) {
            elements.fileSizeBefore.textContent = formatFileSize(data.file_size_before);
        }

        if (elements.fileSizeAfter && data.file_size_after) {
            elements.fileSizeAfter.textContent = formatFileSize(data.file_size_after);
        }

        // Show compression ratio
        if (elements.compressionRatio && data.compression_ratio) {
            elements.compressionRatio.textContent = data.compression_ratio + '%';
        }
    }

    /**
     * Show error message
     */
    function showError(message) {
        if (elements.errorMessage) {
            elements.errorMessage.textContent = message;
            elements.errorMessage.style.display = 'block';
        }
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

    // Expose API
    window.ConversionStatus = {
        start: startPolling,
        stop: stopPolling
    };

})();
