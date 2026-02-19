"""
Tests for backend chat endpoints.
Run from repository root: pytest backend/tests/test_chat.py -v
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Mock psycopg2 and secretmanager before importing main
sys.modules['psycopg2'] = MagicMock()
sys.modules['google.cloud.secretmanager'] = MagicMock()

from main import app, generate_chat_response


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestChatEndpoint:
    """Tests for POST /api/chat endpoint."""

    def test_chat_success(self, client):
        """Test successful chat message processing."""
        response = client.post('/api/chat',
                               data=json.dumps({'message': 'Hola'}),
                               content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert 'response' in data
        assert isinstance(data['response'], str)

    def test_chat_empty_message(self, client):
        """Test chat with empty message returns 400."""
        response = client.post('/api/chat',
                               data=json.dumps({'message': ''}),
                               content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['status'] == 'error'
        assert 'No message provided' in data['message']

    def test_chat_no_message_field(self, client):
        """Test chat with missing message field returns 400."""
        response = client.post('/api/chat',
                               data=json.dumps({}),
                               content_type='application/json')
        
        assert response.status_code == 400

    def test_chat_message_too_long(self, client):
        """Test chat with message exceeding 5000 characters returns 400."""
        long_message = 'a' * 5001
        response = client.post('/api/chat',
                               data=json.dumps({'message': long_message}),
                               content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'too long' in data['message'].lower()

    def test_chat_with_user_id(self, client):
        """Test chat with custom user_id."""
        response = client.post('/api/chat',
                               data=json.dumps({
                                   'message': 'Hola',
                                   'user_id': 'test_user_123'
                               }),
                               content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'


class TestConversationsEndpoint:
    """Tests for GET /api/conversations endpoint."""

    def test_conversations_invalid_limit_string(self, client):
        """Test conversations with non-numeric limit returns 400."""
        response = client.get('/api/conversations?limit=abc')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'Invalid limit' in data['message']

    def test_conversations_limit_too_high(self, client):
        """Test conversations with limit > 100 returns 400."""
        response = client.get('/api/conversations?limit=999')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'between 1 and 100' in data['message']

    def test_conversations_limit_too_low(self, client):
        """Test conversations with limit < 1 returns 400."""
        response = client.get('/api/conversations?limit=0')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'between 1 and 100' in data['message']

    def test_conversations_default_limit(self, client):
        """Test conversations with no limit uses default (20)."""
        # Without DB, should return 500, but validates parameters first
        response = client.get('/api/conversations')
        # Will return 500 because no DB available, but that's after validation passed
        assert response.status_code == 500


class TestChatResponseGeneration:
    """Tests for generate_chat_response function."""

    def test_cotizacion_keyword(self):
        """Test response to cotización keyword."""
        response = generate_chat_response('Necesito una cotización')
        assert 'cotización' in response.lower()
        assert 'panel' in response.lower()

    def test_precio_keyword(self):
        """Test response to precio keyword."""
        response = generate_chat_response('Cuál es el precio?')
        assert 'precio' in response.lower()

    def test_greeting_keyword(self):
        """Test response to greeting."""
        response = generate_chat_response('Hola')
        assert 'hola' in response.lower() or 'bienvenido' in response.lower()

    def test_ayuda_keyword(self):
        """Test response to ayuda keyword."""
        response = generate_chat_response('Ayuda por favor')
        assert 'ayuda' in response.lower() or 'puedo' in response.lower()

    def test_generic_message(self):
        """Test response to generic message."""
        response = generate_chat_response('random message here')
        assert isinstance(response, str)
        assert len(response) > 0


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self, client):
        """Test health endpoint returns 200."""
        response = client.get('/health')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert data['service'] == 'backend'
