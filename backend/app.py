from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import os
import json

app = Flask(__name__)
CORS(app, origins=["http://localhost", "http://localhost:80"])
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET', 'fallback-secret-key')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=7)

bcrypt = Bcrypt(app)
jwt = JWTManager(app)

# Database connection
def get_db_connection():
    conn = psycopg2.connect(
        host='postgres',
        database='chatdb',
        user='chat_user',
        password='chat_password'
    )
    return conn

# User Registration
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return jsonify({'error': 'All fields are required'}), 400

    password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Check if user already exists
        cur.execute("SELECT id FROM users WHERE username = %s OR email = %s", (username, email))
        if cur.fetchone():
            return jsonify({'error': 'User already exists'}), 400

        # Create new user
        cur.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s) RETURNING id",
            (username, email, password_hash)
        )
        user_id = cur.fetchone()[0]
        conn.commit()

        # Create access token
        access_token = create_access_token(identity=user_id)

        return jsonify({
            'message': 'User created successfully',
            'access_token': access_token,
            'user_id': user_id,
            'username': username
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

# User Login
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()

        if user and bcrypt.check_password_hash(user['password_hash'], password):
            # Update last login
            cur.execute("UPDATE users SET last_login = %s WHERE id = %s", (datetime.now(), user['id']))
            conn.commit()

            access_token = create_access_token(identity=user['id'])

            return jsonify({
                'message': 'Login successful',
                'access_token': access_token,
                'user_id': user['id'],
                'username': user['username']
            }), 200
        else:
            return jsonify({'error': 'Invalid credentials'}), 401

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

# Get user chat sessions
@app.route('/api/sessions', methods=['GET'])
@jwt_required()
def get_sessions():
    user_id = get_jwt_identity()

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT * FROM chat_sessions 
            WHERE user_id = %s 
            ORDER BY updated_at DESC
        """, (user_id,))
        sessions = cur.fetchall()

        return jsonify({'sessions': sessions}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

# Create new chat session
@app.route('/api/sessions', methods=['POST'])
@jwt_required()
def create_session():
    user_id = get_jwt_identity()
    data = request.get_json()
    session_name = data.get('session_name', 'New Chat')

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO chat_sessions (user_id, session_name) VALUES (%s, %s) RETURNING id",
            (user_id, session_name)
        )
        session_id = cur.fetchone()[0]
        conn.commit()

        return jsonify({'session_id': session_id, 'session_name': session_name}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

# Save chat message
@app.route('/api/messages', methods=['POST'])
@jwt_required()
def save_message():
    user_id = get_jwt_identity()
    data = request.get_json()
    
    session_id = data.get('session_id')
    user_message = data.get('user_message')
    gemini_response = data.get('gemini_response')
    is_voice = data.get('is_voice', False)
    voice_transcript = data.get('voice_transcript')

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Save chat message
        cur.execute("""
            INSERT INTO chat_messages (session_id, user_message, gemini_response, is_voice, voice_transcript)
            VALUES (%s, %s, %s, %s, %s)
        """, (session_id, user_message, gemini_response, is_voice, voice_transcript))

        # Update session updated_at
        cur.execute("""
            UPDATE chat_sessions SET updated_at = %s WHERE id = %s
        """, (datetime.now(), session_id))

        conn.commit()

        return jsonify({'message': 'Message saved successfully'}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

# Get chat history for a session
@app.route('/api/sessions/<int:session_id>/messages', methods=['GET'])
@jwt_required()
def get_session_messages(session_id):
    user_id = get_jwt_identity()

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Verify session belongs to user
        cur.execute("SELECT user_id FROM chat_sessions WHERE id = %s", (session_id,))
        session = cur.fetchone()
        
        if not session or session['user_id'] != user_id:
            return jsonify({'error': 'Session not found'}), 404

        # Get messages
        cur.execute("""
            SELECT * FROM chat_messages 
            WHERE session_id = %s 
            ORDER BY created_at ASC
        """, (session_id,))
        messages = cur.fetchall()

        return jsonify({'messages': messages}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

# Export chat history
@app.route('/api/sessions/<int:session_id>/export', methods=['GET'])
@jwt_required()
def export_session(session_id):
    user_id = get_jwt_identity()

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Verify session belongs to user and get session info
        cur.execute("""
            SELECT cs.*, u.username 
            FROM chat_sessions cs 
            JOIN users u ON cs.user_id = u.id 
            WHERE cs.id = %s AND cs.user_id = %s
        """, (session_id, user_id))
        session = cur.fetchone()
        
        if not session:
            return jsonify({'error': 'Session not found'}), 404

        # Get all messages
        cur.execute("""
            SELECT * FROM chat_messages 
            WHERE session_id = %s 
            ORDER BY created_at ASC
        """, (session_id,))
        messages = cur.fetchall()

        # Prepare export data
        export_data = {
            'session_info': {
                'session_name': session['session_name'],
                'username': session['username'],
                'created_at': session['created_at'].isoformat(),
                'updated_at': session['updated_at'].isoformat()
            },
            'messages': [
                {
                    'user_message': msg['user_message'],
                    'gemini_response': msg['gemini_response'],
                    'is_voice': msg['is_voice'],
                    'voice_transcript': msg['voice_transcript'],
                    'timestamp': msg['created_at'].isoformat()
                }
                for msg in messages
            ]
        }

        return jsonify(export_data), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

# Save voice history
@app.route('/api/voice-history', methods=['POST'])
@jwt_required()
def save_voice_history():
    user_id = get_jwt_identity()
    data = request.get_json()
    transcript = data.get('transcript')

    if not transcript:
        return jsonify({'error': 'Transcript is required'}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO voice_history (user_id, transcript) VALUES (%s, %s) RETURNING id",
            (user_id, transcript)
        )
        conn.commit()

        return jsonify({'message': 'Voice history saved successfully'}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

# Get voice history
@app.route('/api/voice-history', methods=['GET'])
@jwt_required()
def get_voice_history():
    user_id = get_jwt_identity()

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT * FROM voice_history 
            WHERE user_id = %s 
            ORDER BY created_at DESC
        """, (user_id,))
        voice_history = cur.fetchall()

        return jsonify({'voice_history': voice_history}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)