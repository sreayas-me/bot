document.addEventListener('DOMContentLoaded', function() {
    // Update uptime counter
    const initialServerTime = Math.floor(Date.now() / 1000);
    
    function updateUptime() {
        const uptimeElement = document.getElementById('uptime');
        if (!uptimeElement) return;

        const botStartTime = parseInt(uptimeElement.dataset.uptime);
        const currentServerTime = initialServerTime + Math.floor((Date.now() - window.performance.timeOrigin) / 1000);
        const diff = currentServerTime - botStartTime;
        
        // Ensure diff is not negative
        if (diff < 0) {
            uptimeElement.textContent = '0d 0h 0m 0s';
            return;
        }
        
        const days = Math.floor(diff / 86400);
        const hours = Math.floor((diff % 86400) / 3600);
        const minutes = Math.floor((diff % 3600) / 60);
        const seconds = diff % 60;
        
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
});
