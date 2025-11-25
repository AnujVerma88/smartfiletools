/**
 * Main JavaScript File
 * Core functionality and utilities for SmartFileTools platform
 */

(function() {
    'use strict';

    // Initialize when DOM is ready
    document.addEventListener('DOMContentLoaded', function() {
        initializeApp();
    });

    /**
     * Initialize application
     */
    function initializeApp() {
        initializeNavigation();
        initializeMessages();
        initializeModals();
        initializeTooltips();
        initializeDropdowns();
        initializeFormValidation();
    }

    /**
     * Initialize navigation
     */
    function initializeNavigation() {
        // Mobile menu toggle
        const hamburger = document.querySelector('.hamburger-menu');
        const mobileNav = document.querySelector('.mobile-nav');
        
        if (hamburger && mobileNav) {
            hamburger.addEventListener('click', function() {
                this.classList.toggle('active');
                mobileNav.classList.toggle('active');
                document.body.classList.toggle('menu-open');
            });

            // Close mobile menu when clicking outside
            document.addEventListener('click', function(e) {
                if (!hamburger.contains(e.target) && !mobileNav.contains(e.target)) {
                    hamburger.classList.remove('active');
                    mobileNav.classList.remove('active');
                    document.body.classList.remove('menu-open');
                }
            });
        }

        // User menu dropdown
        const userAvatar = document.querySelector('.user-avatar');
        const userDropdown = document.querySelector('.user-menu .dropdown');
        
        if (userAvatar && userDropdown) {
            userAvatar.addEventListener('click', function(e) {
                e.stopPropagation();
                userDropdown.classList.toggle('active');
            });

            // Close dropdown when clicking outside
            document.addEventListener('click', function(e) {
                if (!userAvatar.contains(e.target) && !userDropdown.contains(e.target)) {
                    userDropdown.classList.remove('active');
                }
            });
        }

        // Highlight active nav link
        highlightActiveNavLink();
    }

    /**
     * Highlight active navigation link
     */
    function highlightActiveNavLink() {
        const currentPath = window.location.pathname;
        const navLinks = document.querySelectorAll('.main-nav a, .mobile-nav a');
        
        navLinks.forEach(link => {
            if (link.getAttribute('href') === currentPath) {
                link.classList.add('active');
            }
        });
    }

    /**
     * Initialize message alerts
     */
    function initializeMessages() {
        const messages = document.querySelectorAll('.alert');
        
        messages.forEach(message => {
            // Auto-dismiss after 5 seconds
            setTimeout(() => {
                dismissMessage(message);
            }, 5000);

            // Close button
            const closeBtn = message.querySelector('.close');
            if (closeBtn) {
                closeBtn.addEventListener('click', () => {
                    dismissMessage(message);
                });
            }
        });
    }

    /**
     * Dismiss message alert
     */
    function dismissMessage(message) {
        message.style.opacity = '0';
        setTimeout(() => {
            message.remove();
        }, 300);
    }

    /**
     * Initialize modals
     */
    function initializeModals() {
        // Modal triggers
        const modalTriggers = document.querySelectorAll('[data-modal-target]');
        
        modalTriggers.forEach(trigger => {
            trigger.addEventListener('click', function(e) {
                e.preventDefault();
                const modalId = this.dataset.modalTarget;
                openModal(modalId);
            });
        });

        // Modal close buttons
        const modalCloseButtons = document.querySelectorAll('.modal-close, [data-modal-close]');
        
        modalCloseButtons.forEach(button => {
            button.addEventListener('click', function() {
                const modal = this.closest('.modal');
                if (modal) {
                    closeModal(modal.id);
                }
            });
        });

        // Close modal when clicking outside
        document.addEventListener('click', function(e) {
            if (e.target.classList.contains('modal')) {
                closeModal(e.target.id);
            }
        });

        // Close modal on Escape key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                const openModal = document.querySelector('.modal.active');
                if (openModal) {
                    closeModal(openModal.id);
                }
            }
        });
    }

    /**
     * Open modal
     */
    function openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('active');
            document.body.style.overflow = 'hidden';
        }
    }

    /**
     * Close modal
     */
    function closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('active');
            document.body.style.overflow = '';
        }
    }

    /**
     * Initialize tooltips
     */
    function initializeTooltips() {
        const tooltipElements = document.querySelectorAll('[data-tooltip]');
        
        tooltipElements.forEach(element => {
            element.addEventListener('mouseenter', function() {
                showTooltip(this, this.dataset.tooltip);
            });

            element.addEventListener('mouseleave', function() {
                hideTooltip();
            });
        });
    }

    /**
     * Show tooltip
     */
    function showTooltip(element, text) {
        const tooltip = document.createElement('div');
        tooltip.className = 'tooltip';
        tooltip.textContent = text;
        tooltip.id = 'active-tooltip';

        document.body.appendChild(tooltip);

        // Position tooltip
        const rect = element.getBoundingClientRect();
        tooltip.style.top = (rect.top - tooltip.offsetHeight - 10) + 'px';
        tooltip.style.left = (rect.left + rect.width / 2 - tooltip.offsetWidth / 2) + 'px';

        // Fade in
        setTimeout(() => {
            tooltip.style.opacity = '1';
        }, 10);
    }

    /**
     * Hide tooltip
     */
    function hideTooltip() {
        const tooltip = document.getElementById('active-tooltip');
        if (tooltip) {
            tooltip.style.opacity = '0';
            setTimeout(() => {
                tooltip.remove();
            }, 200);
        }
    }

    /**
     * Initialize dropdowns
     */
    function initializeDropdowns() {
        const dropdownToggles = document.querySelectorAll('[data-dropdown-toggle]');
        
        dropdownToggles.forEach(toggle => {
            toggle.addEventListener('click', function(e) {
                e.stopPropagation();
                const dropdownId = this.dataset.dropdownToggle;
                const dropdown = document.getElementById(dropdownId);
                
                if (dropdown) {
                    // Close other dropdowns
                    document.querySelectorAll('.dropdown.active').forEach(d => {
                        if (d.id !== dropdownId) {
                            d.classList.remove('active');
                        }
                    });

                    // Toggle this dropdown
                    dropdown.classList.toggle('active');
                }
            });
        });

        // Close dropdowns when clicking outside
        document.addEventListener('click', function() {
            document.querySelectorAll('.dropdown.active').forEach(dropdown => {
                dropdown.classList.remove('active');
            });
        });
    }

    /**
     * Initialize form validation
     */
    function initializeFormValidation() {
        const forms = document.querySelectorAll('form[data-validate]');
        
        forms.forEach(form => {
            form.addEventListener('submit', function(e) {
                if (!validateForm(this)) {
                    e.preventDefault();
                }
            });

            // Real-time validation
            const inputs = form.querySelectorAll('input, textarea, select');
            inputs.forEach(input => {
                input.addEventListener('blur', function() {
                    validateField(this);
                });
            });
        });
    }

    /**
     * Validate form
     */
    function validateForm(form) {
        let isValid = true;
        const inputs = form.querySelectorAll('input[required], textarea[required], select[required]');
        
        inputs.forEach(input => {
            if (!validateField(input)) {
                isValid = false;
            }
        });

        return isValid;
    }

    /**
     * Validate individual field
     */
    function validateField(field) {
        const value = field.value.trim();
        let isValid = true;
        let errorMessage = '';

        // Required validation
        if (field.hasAttribute('required') && !value) {
            isValid = false;
            errorMessage = 'This field is required';
        }

        // Email validation
        if (field.type === 'email' && value) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(value)) {
                isValid = false;
                errorMessage = 'Please enter a valid email address';
            }
        }

        // Min length validation
        if (field.hasAttribute('minlength') && value) {
            const minLength = parseInt(field.getAttribute('minlength'));
            if (value.length < minLength) {
                isValid = false;
                errorMessage = `Minimum length is ${minLength} characters`;
            }
        }

        // Show/hide error
        if (isValid) {
            removeFieldError(field);
        } else {
            showFieldError(field, errorMessage);
        }

        return isValid;
    }

    /**
     * Show field error
     */
    function showFieldError(field, message) {
        field.classList.add('error');
        
        // Remove existing error message
        const existingError = field.parentElement.querySelector('.field-error');
        if (existingError) {
            existingError.remove();
        }

        // Add new error message
        const errorElement = document.createElement('div');
        errorElement.className = 'field-error';
        errorElement.textContent = message;
        field.parentElement.appendChild(errorElement);
    }

    /**
     * Remove field error
     */
    function removeFieldError(field) {
        field.classList.remove('error');
        const errorElement = field.parentElement.querySelector('.field-error');
        if (errorElement) {
            errorElement.remove();
        }
    }

    /**
     * Utility: Format file size
     */
    window.formatFileSize = function(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
    };

    /**
     * Utility: Debounce function
     */
    window.debounce = function(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    };

    /**
     * Utility: Get CSRF token
     */
    window.getCsrfToken = function() {
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
    };

    // Expose API
    window.App = {
        openModal: openModal,
        closeModal: closeModal,
        showTooltip: showTooltip,
        hideTooltip: hideTooltip,
        dismissMessage: dismissMessage
    };

})();
