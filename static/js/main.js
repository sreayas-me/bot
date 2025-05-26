document.addEventListener('DOMContentLoaded', function() {
    // Update uptime counter
    function updateUptime() {
        const uptimeElement = document.getElementById('uptime');
        if (!uptimeElement) return;

        const uptime = parseInt(uptimeElement.dataset.uptime);
        const now = Math.floor(Date.now() / 1000);
        const diff = now - (uptime + initialDiff);
        
        const days = Math.floor(diff / 86400);
        const hours = Math.floor((diff % 86400) / 3600);
        const minutes = Math.floor((diff % 3600) / 60);
        
        uptimeElement.textContent = `${days}d ${hours}h ${minutes}m`;
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
        });
    }

    // Initialize uptime
    const initialDiff = Math.floor(Date.now() / 1000) - parseInt(document.getElementById('uptime')?.dataset.uptime || 0);
    setInterval(updateUptime, 60000);
    updateUptime();
});
