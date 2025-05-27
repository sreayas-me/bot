document.addEventListener('DOMContentLoaded', () => {
    const prefixInput = document.getElementById('newPrefix');
    const prefixContainer = document.getElementById('prefixContainer');
    const prefixesInput = document.getElementById('prefixesInput');

    // Add new prefix
    prefixInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            const prefix = prefixInput.value.trim();
            if (prefix && prefix.length <= 5) {
                addPrefix(prefix);
                prefixInput.value = '';
                updateHiddenInput();
            }
        }
    });

    // Remove prefix
    prefixContainer.addEventListener('click', (e) => {
        if (e.target.classList.contains('remove-prefix')) {
            const tag = e.target.parentElement;
            // Don't remove if it's the last prefix
            const remainingPrefixes = prefixContainer.querySelectorAll('.prefix-tag').length;
            if (remainingPrefixes > 1) {
                tag.remove();
                updateHiddenInput();
            }
        }
    });

    // Add prefix helper
    function addPrefix(prefix) {
        const existingPrefixes = Array.from(prefixContainer.querySelectorAll('.prefix-tag'))
            .map(tag => tag.getAttribute('data-prefix'));
        
        if (!existingPrefixes.includes(prefix)) {
            const tag = document.createElement('button');
            tag.type = 'button';
            tag.className = 'prefix-tag';
            tag.setAttribute('data-prefix', prefix);
            tag.innerHTML = `${prefix}<span class="remove-prefix">×</span>`;
            prefixContainer.appendChild(tag);
        }
    }

    // Update hidden input
    function updateHiddenInput() {
        const prefixes = Array.from(prefixContainer.querySelectorAll('.prefix-tag'))
            .map(tag => tag.getAttribute('data-prefix'));
        prefixesInput.value = prefixes.join(',');
        
        // Update counter
        const counter = document.querySelector('.prefix-counter');
        if (counter) {
            counter.textContent = `${prefixes.length} total prefixes`;
        }
    }
});
