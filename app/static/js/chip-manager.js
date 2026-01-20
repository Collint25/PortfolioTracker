/**
 * Chip multiselect management for filter UI.
 * Handles adding/removing chips and syncing with HTMX filter forms.
 */

/**
 * Removes a chip from the multiselect and triggers filter update.
 * @param {HTMLButtonElement} btn - The remove button inside the chip
 */
function removeChip(btn) {
    const chip = btn.closest('.chip');
    const value = chip.dataset.value;
    const multiselect = chip.closest('[data-multiselect]');

    // Show the option again in dropdown
    if (multiselect) {
        const optionItem = multiselect.querySelector(`li[data-option-value="${value}"]`);
        if (optionItem) {
            optionItem.style.display = '';
        }
    }

    // Blur the dropdown to prevent it from opening
    const dropdownTrigger = multiselect?.querySelector('[tabindex="0"]');
    if (dropdownTrigger) {
        dropdownTrigger.blur();
    }
    document.activeElement?.blur();

    chip.remove();
    dispatchFilterChanged();
}

/**
 * Adds a chip to the multiselect container.
 * @param {string} name - The form field name (e.g., 'type', 'tag_id')
 * @param {string} value - The value for the hidden input
 * @param {string} label - Display text for the chip
 * @param {HTMLElement} [element] - Optional triggering element to close dropdown
 */
function addChip(name, value, label, element) {
    const multiselect = document.querySelector(`[data-multiselect="${name}"]`);
    const container = multiselect.querySelector('.flex-wrap');

    // Check if already exists
    if (container.querySelector(`[data-value="${value}"]`)) {
        return;
    }

    // Create chip
    const chip = document.createElement('span');
    chip.className = 'badge badge-sm badge-primary gap-0.5 chip';
    chip.dataset.value = value;
    chip.innerHTML = `
        ${label}
        <button type="button" tabindex="-1" onmousedown="event.preventDefault(); event.stopPropagation();" onclick="event.stopPropagation(); removeChip(this)" class="ml-0.5 hover:text-primary-content/50">&times;</button>
        <input type="hidden" name="${name}" value="${value}" />
    `;

    // Insert before the add indicator ("+")
    const addIndicator = container.querySelector('.add-indicator');
    if (addIndicator) {
        container.insertBefore(chip, addIndicator);
    } else {
        // Fallback for autocomplete inputs
        const input = container.querySelector('.chip-input');
        container.insertBefore(chip, input);
    }

    // Hide the selected option from dropdown
    const optionItem = multiselect.querySelector(`li[data-option-value="${value}"]`);
    if (optionItem) {
        optionItem.style.display = 'none';
    }

    // Close dropdown
    if (element) {
        element.closest('.dropdown')?.blur();
        document.activeElement?.blur();
    }

    dispatchFilterChanged();
}

/**
 * Initialize autocomplete behavior for chip inputs.
 * Called on DOMContentLoaded and after HTMX swaps.
 */
function initChipAutocomplete() {
    document.querySelectorAll('.chip-input[data-autocomplete]:not([data-autocomplete-initialized])').forEach(input => {
        input.dataset.autocompleteInitialized = 'true';
        let dropdown = null;

        input.addEventListener('input', debounce(async function() {
            const url = this.dataset.autocomplete;
            const name = this.dataset.name;
            const query = this.value.trim();

            if (query.length < 1) {
                if (dropdown) dropdown.remove();
                return;
            }

            const response = await fetch(`${url}?q=${encodeURIComponent(query)}`);
            const symbols = await response.json();

            // Remove existing dropdown
            if (dropdown) dropdown.remove();

            if (symbols.length === 0) return;

            // Create dropdown
            dropdown = document.createElement('ul');
            dropdown.className = 'absolute z-50 menu p-2 shadow bg-base-100 rounded-box w-full max-h-60 overflow-y-auto';
            dropdown.style.top = '100%';
            dropdown.style.left = '0';

            // Get existing values
            const container = this.closest('[data-multiselect]');
            const existing = Array.from(container.querySelectorAll('.chip')).map(c => c.dataset.value);

            symbols.filter(s => !existing.includes(s)).forEach(symbol => {
                const li = document.createElement('li');
                li.innerHTML = `<a>${symbol}</a>`;
                li.querySelector('a').addEventListener('click', () => {
                    addChip(name, symbol, symbol);
                    this.value = '';
                    dropdown.remove();
                    dropdown = null;
                });
                dropdown.appendChild(li);
            });

            this.parentElement.style.position = 'relative';
            this.parentElement.appendChild(dropdown);
        }, 200));

        // Close dropdown on blur
        input.addEventListener('blur', () => {
            setTimeout(() => {
                if (dropdown) {
                    dropdown.remove();
                    dropdown = null;
                }
            }, 200);
        });

        // Handle enter key
        input.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                const value = this.value.trim().toUpperCase();
                if (value) {
                    const name = this.dataset.name;
                    addChip(name, value, value);
                    this.value = '';
                    if (dropdown) {
                        dropdown.remove();
                        dropdown = null;
                    }
                }
            }
        });
    });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', initChipAutocomplete);

// Reinitialize after HTMX swaps (for dynamically loaded content)
document.body.addEventListener('htmx:afterSettle', initChipAutocomplete);
