from app import create_app
from flask_cors import CORS
import os

app = create_app()

# Specify the allowed origins as a list
allowed_origins = ["https://dev.ambicam.com", "https://adminpanel.ambicam.com"]
CORS(app, origins=allowed_origins)

if __name__ == '__main__':
    # Specify the paths to your SSL certificate and private key
    cert_path = os.path.join(os.path.dirname(__file__), 'ambicam.crt')
    key_path = os.path.join(os.path.dirname(__file__), 'ambicam.key')

    # Use the SSL certificate and private key in the app.run method
    app.run(debug=True, host="0.0.0.0", port=443, ssl_context=(cert_path, key_path))
    
    #app.run(debug=True, host="0.0.0.0", port=5000)  # Set debug to False in a production environment
