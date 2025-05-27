import os
from app import app

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

# Add error handlers
@app.errorhandler(500)
def server_error(e):
    return {
        'error': 'Internal Server Error',
        'message': str(e),
        'type': '500'
    }, 500

@app.errorhandler(404)
def not_found(e):
    return {
        'error': 'Not Found',
        'message': str(e),
        'type': '404'
    }, 404
