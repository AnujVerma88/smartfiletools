/**
 * API Key Copy to Clipboard
 * Provides copy-to-clipboard functionality for API keys
 */

(function() {
    'use strict';

    // Initialize when DOM is ready
    document.addEventListener('DOMContentLoaded', function() {
        initializeCopyButtons();
    });

    /**
     * Initialize all copy buttons
     */
    function initializeCopyButtons() {
        const copyButtons = document.querySelectorAll('[data-copy-target]');
        
        copyButtons.forEach(button => {
            button.addEventListener('click', handleCopyClick);
        });
    }

    /**
     * Handle copy button click
     */
    function handleCopyClick(e) {
        e.preventDefault();
        
        const button = e.currentTarget;
        const targetId = button.dataset.copyTarget;
        const targetElement = document.getElementById(targetId);
        
        if (!targetElement) {
            console.error('Copy target not found:', targetId);
            return;
        }

        // Get text to copy
        const textToCopy = targetElement.value || targetElement.textContent || targetElement.innerText;
        
        // Copy to clipboard
        copyToClipboard(textToCopy)
            .then(() => {
                showCopySuccess(button);
            })
            .catch(err => {
                console.error('Failed to copy:', err);
                showCopyError(button);
            });
    }

    /**
     * Copy text to clipboard
     */
    function copyToClipboard(text) {
        // Modern Clipboard API
        if (navigator.clipboard && navigator.clipboard.writeText) {
            return navigator.clipboard.writeText(text);
        }

        // Fallback for older browsers
        return new Promise((resolve, reject) => {
            const textArea = document.createElement('textarea');
            textArea.value = text;
            textArea.style.position = 'fixed';
            textArea.style.left = '-999999px';
            textArea.style.top = '-999999px';
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();

            try {
                const successful = document.execCommand('copy');
                document.body.removeChild(textArea);
                
                if (successful) {
                    resolve();
                } else {
                    reject(new Error('Copy command failed'));
                }
            } catch (err) {
                document.body.removeChild(textArea);
                reject(err);
            }
        });
    }

    /**
     * Show copy success feedback
     */
    function showCopySuccess(button) {
        const originalHTML = button.innerHTML;
        const originalText = button.textContent;

        // Update button to show success
        button.innerHTML = '<i class="fas fa-check"></i> Copied!';
        button.classList.add('btn-success');
        button.disabled = true;

        // Show tooltip if available
        showTooltip(button, 'Copied to clipboard!');

        // Reset after 2 seconds
        setTimeout(() => {
            button.innerHTML = originalHTML;
            button.classList.remove('btn-success');
            button.disabled = false;
        }, 2000);
    }

    /**
     * Show copy error feedback
     */
    function showCopyError(button) {
        const originalHTML = button.innerHTML;

        // Update button to show error
        button.innerHTML = '<i class="fas fa-times"></i> Failed';
        button.classList.add('btn-danger');

        // Show tooltip if available
        showTooltip(button, 'Failed to copy. Please try again.');

        // Reset after 2 seconds
        setTimeout(() => {
            button.innerHTML = originalHTML;
            button.classList.remove('btn-danger');
        }, 2000);
    }

    /**
     * Show tooltip
     */
    function showTooltip(element, message) {
        // Create tooltip element
        const tooltip = document.createElement('div');
        tooltip.className = 'copy-tooltip';
        tooltip.textContent = message;
        tooltip.style.position = 'absolute';
        tooltip.style.zIndex = '9999';

        // Position tooltip
        const rect = element.getBoundingClientRect();
        tooltip.style.top = (rect.top - 40) + 'px';
        tooltip.style.left = (rect.left + rect.width / 2) + 'px';
        tooltip.style.transform = 'translateX(-50%)';

        document.body.appendChild(tooltip);

        // Fade in
        setTimeout(() => {
            tooltip.style.opacity = '1';
        }, 10);

        // Remove after 2 seconds
        setTimeout(() => {
            tooltip.style.opacity = '0';
            setTimeout(() => {
                document.body.removeChild(tooltip);
            }, 300);
        }, 2000);
    }

    /**
     * Copy API key with masking
     */
    window.copyAPIKey = function(keyId, fullKey) {
        copyToClipboard(fullKey)
            .then(() => {
                // Show success message
                const button = document.querySelector(`[data-key-id="${keyId}"]`);
                if (button) {
                    showCopySuccess(button);
                }
            })
            .catch(err => {
                console.error('Failed to copy API key:', err);
                alert('Failed to copy API key. Please copy manually.');
            });
    };

    /**
     * Reveal/hide API key
     */
    window.toggleAPIKeyVisibility = function(keyId) {
        const keyElement = document.getElementById(`api-key-${keyId}`);
        const toggleButton = document.getElementById(`toggle-key-${keyId}`);
        
        if (!keyElement || !toggleButton) return;

        const isHidden = keyElement.dataset.hidden === 'true';

        if (isHidden) {
            // Show full key
            keyElement.textContent = keyElement.dataset.fullKey;
            keyElement.dataset.hidden = 'false';
            toggleButton.innerHTML = '<i class="fas fa-eye-slash"></i> Hide';
        } else {
            // Hide key (show only prefix)
            keyElement.textContent = keyElement.dataset.maskedKey;
            keyElement.dataset.hidden = 'true';
            toggleButton.innerHTML = '<i class="fas fa-eye"></i> Show';
        }
    };

    // Expose API
    window.CopyToClipboard = {
        copy: copyToClipboard,
        copyAPIKey: window.copyAPIKey,
        toggleVisibility: window.toggleAPIKeyVisibility
    };

})();
