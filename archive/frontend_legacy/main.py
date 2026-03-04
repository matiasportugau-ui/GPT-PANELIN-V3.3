"""
Frontend Service - Flask Application
Provides a simple web interface that communicates with the backend service.
Includes a chat interface for the Panelin BMC Uruguay assistant.
"""

import os
from flask import Flask, jsonify, render_template, request
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
    Main route that serves the chat interface.
    """
    return render_template('chat.html')


@app.route('/api/status')
def status():
    """
    Status endpoint that fetches data from the backend service.
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


@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Chat endpoint that processes user messages via backend service.
    Integrates with backend AI processing and conversation storage.
    """
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        user_id = data.get('user_id', 'anonymous')
        
        if not user_message:
            return jsonify({
                'status': 'error',
                'message': 'No message provided'
            }), 400
        
        # Validate message length
        if len(user_message) > 5000:
            return jsonify({
                'status': 'error',
                'message': 'Message too long. Maximum 5000 characters allowed.'
            }), 400
        
        # Forward to backend service
        try:
            response = requests.post(
                f"{BACKEND_SERVICE_URL}/api/chat",
                json={'message': user_message, 'user_id': user_id},
                timeout=30
            )
            backend_data = response.json()

            return jsonify(backend_data), response.status_code
            
        except requests.exceptions.ConnectionError:
            # Fallback response if backend is unavailable
            return jsonify({
                'status': 'success',
                'response': (
                    "El servicio backend no está disponible en este momento. "
                    "Por favor, intenta nuevamente más tarde."
                ),
                'backend_available': False
            }), 200
            
        except requests.exceptions.Timeout:
            return jsonify({
                'status': 'success',
                'response': (
                    "El servicio está tardando más de lo esperado. "
                    "Por favor, intenta nuevamente."
                ),
                'backend_available': False
            }), 200
        
    except Exception as e:
        print(f"Error processing chat: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Error al procesar el mensaje.'
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
