/**
 * Tool Cards Interactive Enhancements
 * Provides additional interactivity for tool card components
 */

(function() {
    'use strict';

    // Initialize tool cards on page load
    document.addEventListener('DOMContentLoaded', function() {
        initToolCards();
        initTouchFeedback();
        initAccessibility();
    });

    /**
     * Initialize tool card interactions
     */
    function initToolCards() {
        const toolCards = document.querySelectorAll('.tool-card');
        
        toolCards.forEach(card => {
            // Add ripple effect on click (optional enhancement)
            card.addEventListener('click', function(e) {
                createRipple(e, this);
            });

            // Track card interactions for analytics (if needed)
            card.addEventListener('click', function() {
                const toolName = this.querySelector('h3')?.textContent;
                if (toolName && typeof trackEvent === 'function') {
                    trackEvent('tool_card_click', { tool: toolName });
                }
            });
        });
    }

    /**
     * Create ripple effect on card click
     */
    function createRipple(event, element) {
        const ripple = document.createElement('span');
        const rect = element.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = event.clientX - rect.left - size / 2;
        const y = event.clientY - rect.top - size / 2;

        ripple.style.width = ripple.style.height = size + 'px';
        ripple.style.left = x + 'px';
        ripple.style.top = y + 'px';
        ripple.classList.add('ripple-effect');

        element.appendChild(ripple);

        setTimeout(() => {
            ripple.remove();
        }, 600);
    }

    /**
     * Enhanced touch feedback for mobile devices
     */
    function initTouchFeedback() {
        if (!('ontouchstart' in window)) return;

        const toolCards = document.querySelectorAll('.tool-card');
        
        toolCards.forEach(card => {
            card.addEventListener('touchstart', function() {
                this.classList.add('touch-active');
            });

            card.addEventListener('touchend', function() {
                setTimeout(() => {
                    this.classList.remove('touch-active');
                }, 150);
            });

            card.addEventListener('touchcancel', function() {
                this.classList.remove('touch-active');
            });
        });
    }

    /**
     * Enhance accessibility features
     */
    function initAccessibility() {
        const toolCards = document.querySelectorAll('.tool-card');
        
        toolCards.forEach(card => {
            const link = card.querySelector('a');
            if (!link) return;

            // Make entire card keyboard accessible
            card.setAttribute('tabindex', '0');
            card.setAttribute('role', 'article');

            // Handle keyboard navigation
            card.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    link.click();
                }
            });

            // Announce card content to screen readers
            const toolName = card.querySelector('h3')?.textContent;
            const toolDesc = card.querySelector('p')?.textContent;
            if (toolName && toolDesc) {
                card.setAttribute('aria-label', `${toolName}: ${toolDesc}`);
            }
        });
    }

    /**
     * Lazy load tool cards (for performance with many cards)
     */
    function initLazyLoading() {
        if ('IntersectionObserver' in window) {
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('visible');
                        observer.unobserve(entry.target);
                    }
                });
            }, {
                rootMargin: '50px'
            });

            document.querySelectorAll('.tool-card').forEach(card => {
                observer.observe(card);
            });
        }
    }

    /**
     * Filter tool cards by search query
     */
    window.filterToolCards = function(query) {
        const toolCards = document.querySelectorAll('.tool-card');
        const searchTerm = query.toLowerCase().trim();

        toolCards.forEach(card => {
            const toolName = card.querySelector('h3')?.textContent.toLowerCase() || '';
            const toolDesc = card.querySelector('p')?.textContent.toLowerCase() || '';
            
            if (toolName.includes(searchTerm) || toolDesc.includes(searchTerm)) {
                card.style.display = '';
                card.classList.remove('hidden');
            } else {
                card.style.display = 'none';
                card.classList.add('hidden');
            }
        });

        // Show "no results" message if all cards are hidden
        const visibleCards = document.querySelectorAll('.tool-card:not(.hidden)');
        const noResultsMsg = document.getElementById('no-results-message');
        
        if (noResultsMsg) {
            noResultsMsg.style.display = visibleCards.length === 0 ? 'block' : 'none';
        }
    };

    /**
     * Sort tool cards by different criteria
     */
    window.sortToolCards = function(criteria) {
        const grid = document.querySelector('.tools-grid');
        if (!grid) return;

        const cards = Array.from(grid.querySelectorAll('.tool-card'));
        
        cards.sort((a, b) => {
            switch(criteria) {
                case 'name':
                    const nameA = a.querySelector('h3')?.textContent || '';
                    const nameB = b.querySelector('h3')?.textContent || '';
                    return nameA.localeCompare(nameB);
                
                case 'popular':
                    const usageA = parseInt(a.querySelector('.usage-count span')?.textContent) || 0;
                    const usageB = parseInt(b.querySelector('.usage-count span')?.textContent) || 0;
                    return usageB - usageA;
                
                default:
                    return 0;
            }
        });

        // Re-append sorted cards
        cards.forEach(card => grid.appendChild(card));
    };

})();
