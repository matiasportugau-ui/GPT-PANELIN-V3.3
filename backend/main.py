"""
Backend Service - Flask Application
Connects to Cloud SQL (PostgreSQL) using credentials from Secret Manager.
Provides chat conversation storage and processing endpoints.
"""

import os
import json
from flask import Flask, jsonify, request

# Optional imports for GCP
try:
    import psycopg2
    from google.cloud import secretmanager
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    print("Warning: Database modules not available. Running in standalone mode.")

app = Flask(__name__)

# Configuration from environment variables
PORT = int(os.environ.get('PORT', 8080))
PROJECT_ID = os.environ.get('PROJECT_ID', '')
DB_CONNECTION_NAME = os.environ.get('DB_CONNECTION_NAME', '')
DB_USER = os.environ.get('DB_USER', 'postgres')
DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
DB_NAME = os.environ.get('DB_NAME', 'app_database')


def get_secret(secret_name):
    """
    Retrieve secret value from Google Cloud Secret Manager.
    
    Args:
        secret_name (str): Name of the secret to retrieve
        
    Returns:
        str: Secret value
    """
    if not DB_AVAILABLE:
        return None
        
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{PROJECT_ID}/secrets/{secret_name}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode('UTF-8')
    except Exception as e:
        print(f"Error retrieving secret {secret_name}: {str(e)}")
        return None


def get_db_connection():
    """
    Create a connection to Cloud SQL PostgreSQL database.
    Uses Unix socket connection for Cloud Run to Cloud SQL proxy.
    
    Returns:
        psycopg2.connection: Database connection object or None
    """
    if not DB_AVAILABLE:
        return None
        
    try:
        # Cloud SQL connection using Unix socket
        # Format: /cloudsql/PROJECT_ID:REGION:INSTANCE_NAME
        unix_socket = f'/cloudsql/{DB_CONNECTION_NAME}'
        
        conn = psycopg2.connect(
            host=unix_socket,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        return conn
    except Exception as e:
        print(f"Error connecting to database: {str(e)}")
        return None


@app.route('/api/data')
def get_data():
    """
    API endpoint that queries the database and returns data.
    Creates a test table and inserts sample data if it doesn't exist.
    """
    conn = None
    cursor = None
    
    try:
        # Get database connection
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'status': 'error',
                'message': 'Could not connect to database'
            }), 500
        
        cursor = conn.cursor()
        
        # Create test table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS app_data (
                id SERIAL PRIMARY KEY,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert sample data if table is empty
        cursor.execute("SELECT COUNT(*) FROM app_data")
        count = cursor.fetchone()[0]
        
        if count == 0:
            cursor.execute("""
                INSERT INTO app_data (message) 
                VALUES ('Hello from Cloud SQL!')
            """)
            conn.commit()
        
        # Query database version
        cursor.execute("SELECT VERSION()")
        db_version = cursor.fetchone()[0]
        
        # Query sample data
        cursor.execute("SELECT id, message, created_at FROM app_data LIMIT 5")
        rows = cursor.fetchall()
        
        data = []
        for row in rows:
            data.append({
                'id': row[0],
                'message': row[1],
                'created_at': str(row[2])
            })
        
        return jsonify({
            'status': 'success',
            'database_version': db_version,
            'data': data,
            'connection_name': DB_CONNECTION_NAME
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Database error: {str(e)}'
        }), 500
        
    finally:
        # Clean up database connections
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route('/api/chat', methods=['POST'])
def process_chat():
    """
    Process chat messages and store conversations.
    Stores conversation in database and returns AI-generated response.
    """
    conn = None
    cursor = None
    
    try:
        # Get message from request
        data = request.get_json()
        user_message = data.get('message', '')
        user_id = data.get('user_id', 'anonymous')
        
        # Input validation
        if not user_message:
            return jsonify({
                'status': 'error',
                'message': 'No message provided'
            }), 400
        
        # Validate message length (max 5000 characters)
        if len(user_message) > 5000:
            return jsonify({
                'status': 'error',
                'message': 'Message too long. Maximum 5000 characters allowed.'
            }), 400
        
        # Generate response (works with or without DB)
        bot_response = generate_chat_response(user_message)
        
        # Try to store in database if available
        db_stored = False
        conversation_id = None
        created_at = None
        
        if DB_AVAILABLE:
            conn = get_db_connection()
            if conn:
                try:
                    cursor = conn.cursor()
                    
                    # Store conversation in database
                    # Note: conversations table must be created via migrations/init script
                    cursor.execute("""
                        INSERT INTO conversations (user_id, user_message, bot_response)
                        VALUES (%s, %s, %s)
                        RETURNING id, created_at
                    """, (user_id, user_message, bot_response))
                    
                    result = cursor.fetchone()
                    conversation_id = result[0]
                    created_at = result[1]
                    db_stored = True
                    
                    conn.commit()
                except Exception as db_error:
                    print(f"DB storage error: {str(db_error)}")
        
        response_data = {
            'status': 'success',
            'response': bot_response,
            'db_stored': db_stored
        }
        
        if conversation_id:
            response_data['conversation_id'] = conversation_id
            response_data['created_at'] = str(created_at)
        
        return jsonify(response_data), 200
        
    except Exception as e:
        print(f"Error processing chat: {str(e)}")
        # Return generic error without exposing internal details
        return jsonify({
            'status': 'error',
            'message': 'Error al procesar el mensaje. Por favor, intenta nuevamente.'
        }), 500
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route('/api/conversations', methods=['GET'])
def get_conversations():
    """
    Retrieve conversation history for a user.
    Optional query parameter: user_id
    """
    conn = None
    cursor = None
    
    try:
        user_id = request.args.get('user_id', 'anonymous')
        limit_param = request.args.get('limit', '20')
        
        # Validate limit parameter
        try:
            limit = int(limit_param)
            if limit < 1 or limit > 100:
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid limit parameter. Must be an integer between 1 and 100.'
                }), 400
        except ValueError:
            return jsonify({
                'status': 'error',
                'message': 'Invalid limit parameter. Must be an integer.'
            }), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'status': 'error',
                'message': 'Could not connect to database'
            }), 500
        
        cursor = conn.cursor()
        
        # Query conversations
        cursor.execute("""
            SELECT id, user_message, bot_response, created_at
            FROM conversations
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """, (user_id, limit))
        
        rows = cursor.fetchall()
        
        conversations = []
        for row in rows:
            conversations.append({
                'id': row[0],
                'user_message': row[1],
                'bot_response': row[2],
                'created_at': str(row[3])
            })
        
        return jsonify({
            'status': 'success',
            'conversations': conversations,
            'count': len(conversations)
        }), 200
        
    except Exception as e:
        print(f"Error retrieving conversations: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Error al recuperar las conversaciones.'
        }), 500
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def generate_chat_response(user_message):
    """
    Generate AI response to user message.
    TODO: Integrate with Wolf API KB Write and GPT for intelligent responses.
    
    Args:
        user_message (str): User's message
        
    Returns:
        str: Bot response
    """
    # Simple keyword-based responses for now
    message_lower = user_message.lower()
    
    if 'cotización' in message_lower or 'cotizacion' in message_lower:
        return (
            "¡Claro! Puedo ayudarte con una cotización de paneles BMC Uruguay. "
            "Para darte el mejor precio, necesito saber:\n"
            "1. ¿Qué tipo de panel necesitas? (ISOPANEL, ISODEC, ISOROOF)\n"
            "2. ¿Qué espesor? (50mm, 80mm, 100mm, etc.)\n"
            "3. ¿Cuántos metros cuadrados necesitas?"
        )
    elif 'precio' in message_lower:
        return (
            "Los precios de nuestros paneles varían según el tipo y espesor. "
            "¿Qué panel específico te interesa? Por ejemplo: ISOPANEL EPS 50mm, ISODEC PIR 100mm, etc."
        )
    elif any(word in message_lower for word in ['hola', 'buenos días', 'buenas tardes']):
        return (
            "¡Hola! Bienvenido a Panelin BMC Uruguay. "
            "Estoy aquí para ayudarte con cotizaciones de paneles aislantes. "
            "¿En qué puedo asistirte?"
        )
    elif 'ayuda' in message_lower or 'help' in message_lower:
        return (
            "Puedo ayudarte con:\n"
            "• Cotizaciones de paneles (ISOPANEL, ISODEC, ISOROOF)\n"
            "• Información técnica de productos\n"
            "• Cálculo de cantidades y accesorios\n"
            "• Asesoramiento sobre instalación\n\n"
            "¿Qué necesitas?"
        )
    else:
        return (
            f"Recibí tu mensaje sobre '{user_message[:50]}...'. "
            "Actualmente estoy en desarrollo y pronto podré ayudarte mejor. "
            "Por ahora, puedo asistirte con cotizaciones básicas de paneles. "
            "¿Te gustaría una cotización?"
        )


@app.route('/health')
def health():
    """
    Health check endpoint for Cloud Run.
    Returns 200 OK if the service is running.
    """
    return jsonify({
        'status': 'healthy',
        'service': 'backend'
    }), 200


if __name__ == '__main__':
    # Run the Flask application
    # Cloud Run will set PORT environment variable
    app.run(host='0.0.0.0', port=PORT)
