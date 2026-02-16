"""
Backend Service - Flask Application
Connects to Cloud SQL (PostgreSQL) using credentials from Secret Manager.
"""

import os
import json
from flask import Flask, jsonify
import psycopg2
from google.cloud import secretmanager

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
        psycopg2.connection: Database connection object
    """
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
