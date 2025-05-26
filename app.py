from flask import Flask, render_template
from werkzeug.serving import make_server

app = Flask(__name__)
server = None

@app.route('/')
def home():
    return render_template('index.html')

def run_server():
    global server
    server = make_server('127.0.0.1', 5000, app)
    server.serve_forever()

def shutdown_server():
    global server
    if server:
        server.shutdown()

def run():
    run_server()

if __name__ == "__main__":
    run()

