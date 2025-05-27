bind = "0.0.0.0:" + str(os.environ.get("PORT", 8000))
workers = 4
threads = 2
timeout = 120
accesslog = "-"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'
loglevel = "info"
