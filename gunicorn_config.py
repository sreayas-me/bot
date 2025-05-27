import os
import socket
import multiprocessing

def get_available_port(start_port, max_port=65535):
    """Find first available port in range"""
    for port in range(start_port, max_port + 1):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('0.0.0.0', port))
                s.close()
                return port
        except OSError:
            continue
    return None

# Binding
default_port = int(os.environ.get("PORT", 5001))  # Changed default to 5001
port = get_available_port(default_port)
if port != default_port:  # If we couldn't get 5001, try other ports
    port = get_available_port(5000)  # Try 5000 next
    if not port:
        port = get_available_port(8000)  # Try alternate port range as last resort
if not port:
    raise RuntimeError("No available ports found")
bind = f"0.0.0.0:{port}"

# Worker processes
workers = int(os.environ.get('WEB_CONCURRENCY', 2))
worker_class = 'gthread'  # Use threads
threads = int(os.environ.get('PYTHON_MAX_THREADS', 4))
worker_connections = 1000

# Timeout
timeout = 120
graceful_timeout = 30
keepalive = 65

# Logging
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get('LOG_LEVEL', 'info')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'
capture_output = True

# SSL and security
forwarded_allow_ips = '*'
secure_scheme_headers = {
    'X-FORWARDED-PROTOCOL': 'ssl',
    'X-FORWARDED-PROTO': 'https',
    'X-FORWARDED-SSL': 'on'
}

# Performance tuning
max_requests = 1000
max_requests_jitter = 50
preload_app = True
reuse_port = True

# Process naming
proc_name = 'bronxbot-web'

# Flask specific
wsgi_app = 'wsgi:app'
pythonpath = '.'

# Error pages
errorlog = '-'
loglevel = 'debug'

# Reload in development
reload = os.environ.get('FLASK_ENV') == 'development'
