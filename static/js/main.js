document.addEventListener('DOMContentLoaded', function() {
    // Update uptime in real-time
    function updateUptime() {
        const uptimeElement = document.getElementById('uptime');
        if (uptimeElement) {
            let seconds = parseInt(uptimeElement.dataset.uptime);
            
            setInterval(() => {
                seconds++;
                const days = Math.floor(seconds / 86400);
                const hours = Math.floor((seconds % 86400) / 3600);
                const minutes = Math.floor((seconds % 3600) / 60);
                uptimeElement.textContent = `${days}d ${hours}h ${minutes}m`;
            }, 1000);
        }
    }

    // Mobile navigation toggle
    const navToggle = document.getElementById('nav-toggle');
    const navLinks = document.querySelector('.nav-links');
    
    if (navToggle) {
        navToggle.addEventListener('click', () => {
            navLinks.classList.toggle('active');
        });
    }

    updateUptime();
});
