document.addEventListener('DOMContentLoaded', function() {
    // Update uptime counter
    const initialServerTime = Math.floor(Date.now() / 1000);
    
    function updateUptime() {
        const uptimeElement = document.getElementById('uptime');
        if (!uptimeElement) return;

        const uptimeSeconds = parseInt(uptimeElement.dataset.uptime);
        
        const days = Math.floor(uptimeSeconds / 86400);
        const hours = Math.floor((uptimeSeconds % 86400) / 3600);
        const minutes = Math.floor((uptimeSeconds % 3600) / 60);
        const seconds = uptimeSeconds % 60;
        
        uptimeElement.textContent = `${days}d ${hours}h ${minutes}m ${seconds}s`;
    }

    // Link hover effect
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('mouseover', () => {
            link.style.transform = 'translateY(-2px)';
        });
        
        link.addEventListener('mouseout', () => {
            link.style.transform = 'translateY(0)';
        });
    });

    // Mobile navigation toggle
    const navToggle = document.getElementById('nav-toggle');
    const navLinks = document.querySelector('.nav-links');
    
    if (navToggle) {
        navToggle.addEventListener('click', () => {
            navLinks.classList.toggle('active');
            navToggle.classList.toggle('active');
        });

        // Close navbar when clicking outside
        document.addEventListener('click', (e) => {
            if (!navLinks.contains(e.target) && 
                !navToggle.contains(e.target) && 
                navLinks.classList.contains('active')) {
                navLinks.classList.remove('active');
                navToggle.classList.remove('active');
            }
        });
    }

    // Collapsible sidebar toggle
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const sidebar = document.querySelector('.sidebar.collapsible');
    
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', () => {
            sidebar.classList.toggle('active');
        });

        // Close sidebar when clicking outside
        document.addEventListener('click', (e) => {
            if (!sidebar.contains(e.target) && 
                !sidebarToggle.contains(e.target) && 
                sidebar.classList.contains('active')) {
                sidebar.classList.remove('active');
            }
        });
    }
    
    // Initialize uptime
    setInterval(updateUptime, 1000);
    updateUptime();

    // Prefix Management
    const prefixInput = document.getElementById('newPrefix');
    const prefixContainer = document.getElementById('prefixContainer');
    const prefixesHiddenInput = document.getElementById('prefixesInput');
    
    if (prefixInput && prefixContainer) {
        // Add new prefix
        prefixInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                const prefix = prefixInput.value.trim();
                if (prefix && !getPrefixes().includes(prefix)) {
                    addPrefix(prefix);
                    prefixInput.value = '';
                    updatePrefixCounter();
                }
            }
        });

        // Remove prefix
        prefixContainer.addEventListener('click', (e) => {
            if (e.target.classList.contains('prefix-tag') || e.target.classList.contains('remove-prefix')) {
                const button = e.target.closest('.prefix-tag');
                if (button && getPrefixes().length > 1) {  // Prevent removing last prefix
                    button.style.animation = 'slideIn 0.3s ease reverse';
                    setTimeout(() => {
                        button.remove();
                        updatePrefixCounter();
                        updateHiddenInput();
                    }, 300);
                }
            }
        });

        function addPrefix(prefix) {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'prefix-tag';
            button.dataset.prefix = prefix;
            button.innerHTML = `${prefix}<span class="remove-prefix">×</span>`;
            prefixContainer.appendChild(button);
            updateHiddenInput();
        }

        function getPrefixes() {
            return Array.from(prefixContainer.children).map(btn => btn.dataset.prefix);
        }

        function updateHiddenInput() {
            prefixesHiddenInput.value = getPrefixes().join(',');
        }

        function updatePrefixCounter() {
            const counter = document.querySelector('.prefix-counter');
            if (counter) {
                const count = getPrefixes().length;
                counter.textContent = `${count} total ${count === 1 ? 'prefix' : 'prefixes'}`;
            }
        }
    }
});
