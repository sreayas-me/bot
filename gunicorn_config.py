import os
import multiprocessing

# Binding
bind = "0.0.0.0:" + str(os.environ.get("PORT", 8000))

# Worker processes
workers = int(os.environ.get('WEB_CONCURRENCY', 2))  # 2 workers by default
worker_class = 'gthread'  # Use threads
threads = int(os.environ.get('PYTHON_MAX_THREADS', 4))  # 4 threads per worker
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

# SSL
forwarded_allow_ips = '*'

# Performance tuning
max_requests = 1000
max_requests_jitter = 50
preload_app = True

# Process naming
proc_name = 'bronxbot-web'
