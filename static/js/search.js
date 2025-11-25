/**
 * Search Functionality
 * Provides real-time search for tools and content
 */

(function() {
    'use strict';

    // Configuration
    const DEBOUNCE_DELAY = 300; // milliseconds

    // State
    let debounceTimer = null;

    // DOM elements
    const elements = {
        searchInput: document.getElementById('searchInput'),
        searchResults: document.getElementById('searchResults'),
        searchClear: document.getElementById('searchClear'),
        noResults: document.getElementById('noResults')
    };

    // Initialize when DOM is ready
    document.addEventListener('DOMContentLoaded', function() {
        if (elements.searchInput) {
            initializeSearch();
        }
    });

    /**
     * Initialize search functionality
     */
    function initializeSearch() {
        // Search input event
        elements.searchInput.addEventListener('input', handleSearchInput);

        // Clear button
        if (elements.searchClear) {
            elements.searchClear.addEventListener('click', clearSearch);
        }

        // Handle Enter key
        elements.searchInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                performSearch(this.value);
            }
        });

        // Close results when clicking outside
        document.addEventListener('click', function(e) {
            if (!elements.searchInput.contains(e.target) && 
                !elements.searchResults?.contains(e.target)) {
                hideResults();
            }
        });
    }

    /**
     * Handle search input with debouncing
     */
    function handleSearchInput(e) {
        const query = e.target.value.trim();

        // Show/hide clear button
        if (elements.searchClear) {
            elements.searchClear.style.display = query ? 'block' : 'none';
        }

        // Clear previous timer
        if (debounceTimer) {
            clearTimeout(debounceTimer);
        }

        // Debounce search
        if (query.length >= 2) {
            debounceTimer = setTimeout(() => {
                performSearch(query);
            }, DEBOUNCE_DELAY);
        } else if (query.length === 0) {
            hideResults();
            // Reset tool cards if on tools page
            if (typeof window.filterToolCards === 'function') {
                window.filterToolCards('');
            }
        }
    }

    /**
     * Perform search
     */
    function performSearch(query) {
        if (!query) {
            hideResults();
            return;
        }

        // If on tools page, filter tool cards
        if (typeof window.filterToolCards === 'function') {
            window.filterToolCards(query);
            return;
        }

        // Otherwise, show search results dropdown
        showLoadingResults();

        // Make AJAX request to search endpoint
        fetch(`/search/?q=${encodeURIComponent(query)}`, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            displayResults(data.results);
        })
        .catch(error => {
            console.error('Search error:', error);
            hideResults();
        });
    }

    /**
     * Display search results
     */
    function displayResults(results) {
        if (!elements.searchResults) return;

        // Clear previous results
        elements.searchResults.innerHTML = '';

        if (results.length === 0) {
            showNoResults();
            return;
        }

        // Create results list
        const resultsList = document.createElement('ul');
        resultsList.className = 'search-results-list';

        results.forEach(result => {
            const li = document.createElement('li');
            li.className = 'search-result-item';

            const link = document.createElement('a');
            link.href = result.url;
            link.innerHTML = `
                <div class="search-result-icon">
                    <i class="${result.icon || 'fas fa-file'}"></i>
                </div>
                <div class="search-result-content">
                    <div class="search-result-title">${highlightQuery(result.title, elements.searchInput.value)}</div>
                    <div class="search-result-description">${result.description || ''}</div>
                </div>
            `;

            li.appendChild(link);
            resultsList.appendChild(li);
        });

        elements.searchResults.appendChild(resultsList);
        elements.searchResults.style.display = 'block';
    }

    /**
     * Show loading state
     */
    function showLoadingResults() {
        if (!elements.searchResults) return;

        elements.searchResults.innerHTML = `
            <div class="search-loading">
                <i class="fas fa-spinner fa-spin"></i>
                <span>Searching...</span>
            </div>
        `;
        elements.searchResults.style.display = 'block';
    }

    /**
     * Show no results message
     */
    function showNoResults() {
        if (!elements.searchResults) return;

        elements.searchResults.innerHTML = `
            <div class="search-no-results">
                <i class="fas fa-search"></i>
                <p>No results found</p>
            </div>
        `;
        elements.searchResults.style.display = 'block';
    }

    /**
     * Hide results
     */
    function hideResults() {
        if (elements.searchResults) {
            elements.searchResults.style.display = 'none';
        }
    }

    /**
     * Clear search
     */
    function clearSearch() {
        if (elements.searchInput) {
            elements.searchInput.value = '';
            elements.searchInput.focus();
        }

        if (elements.searchClear) {
            elements.searchClear.style.display = 'none';
        }

        hideResults();

        // Reset tool cards if on tools page
        if (typeof window.filterToolCards === 'function') {
            window.filterToolCards('');
        }
    }

    /**
     * Highlight search query in text
     */
    function highlightQuery(text, query) {
        if (!query) return text;

        const regex = new RegExp(`(${escapeRegex(query)})`, 'gi');
        return text.replace(regex, '<mark>$1</mark>');
    }

    /**
     * Escape special regex characters
     */
    function escapeRegex(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    // Expose API
    window.Search = {
        perform: performSearch,
        clear: clearSearch
    };

})();
