/**
 * Shared utilities for filter management and debouncing.
 */

/**
 * Creates a debounced version of a function that delays execution until
 * after `ms` milliseconds have elapsed since the last call.
 * @param {Function} fn - The function to debounce
 * @param {number} ms - Delay in milliseconds
 * @returns {Function} Debounced function
 */
function debounce(fn, ms) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => fn.apply(this, args), ms);
    };
}

/**
 * Dispatches a custom 'filterChanged' event on document.body.
 * HTMX forms can listen for this event with hx-trigger="filterChanged from:body".
 */
function dispatchFilterChanged() {
    document.body.dispatchEvent(new CustomEvent('filterChanged'));
}

/**
 * Pre-bound debounced version of dispatchFilterChanged (300ms delay).
 * Use for text inputs: oninput="debouncedFilterChange()"
 */
const debouncedFilterChange = debounce(dispatchFilterChanged, 300);
