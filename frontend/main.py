"""
Frontend Service - Flask Application
Provides a simple web interface that communicates with the backend service.
"""

import os
from flask import Flask, jsonify
import requests

app = Flask(__name__)

# Configuration from environment variables
PORT = int(os.environ.get('PORT', 8080))
# Backend service URL - defaults to Cloud Run internal networking
BACKEND_SERVICE_URL = os.environ.get(
    'BACKEND_SERVICE_URL',
    'http://backend-service.default.svc.run.internal'
)


@app.route('/')
def index():
    """
    Main route that fetches data from the backend service.
    Includes error handling for when backend is unavailable.
    """
    try:
        # Make request to backend service
        response = requests.get(f"{BACKEND_SERVICE_URL}/api/data", timeout=10)
        response.raise_for_status()
        
        backend_data = response.json()
        
        return jsonify({
            'status': 'success',
            'message': 'Frontend service is running',
            'backend_response': backend_data
        }), 200
        
    except requests.exceptions.ConnectionError:
        return jsonify({
            'status': 'error',
            'message': 'Cannot connect to backend service',
            'backend_url': BACKEND_SERVICE_URL
        }), 503
        
    except requests.exceptions.Timeout:
        return jsonify({
            'status': 'error',
            'message': 'Backend service timeout',
            'backend_url': BACKEND_SERVICE_URL
        }), 504
        
    except requests.exceptions.RequestException as e:
        return jsonify({
            'status': 'error',
            'message': f'Error communicating with backend: {str(e)}',
            'backend_url': BACKEND_SERVICE_URL
        }), 500


@app.route('/health')
def health():
    """
    Health check endpoint for Cloud Run.
    Returns 200 OK if the service is running.
    """
    return jsonify({
        'status': 'healthy',
        'service': 'frontend'
    }), 200


if __name__ == '__main__':
    # Run the Flask application
    # Cloud Run will set PORT environment variable
    app.run(host='0.0.0.0', port=PORT)
