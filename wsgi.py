import os
import sys
import pathlib

# Add the dashboard directory to Python path
root_dir = pathlib.Path(__file__).parent.absolute()
dashboard_dir = os.path.join(root_dir, 'dashboard')
sys.path.insert(0, str(dashboard_dir))

# Import the Flask app
from dashboard.app import app as application

# For WSGI servers
app = application

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
