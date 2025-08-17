import os
import json
import sqlite3
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from Utils.ChatAgent import chat_manager
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# Import all agent classes
from Utils.Agents import HealthSummary, FitnessTrainer, Nutritionist, HealthAdvisor
from Utils.ChatAgent import chat_manager
# Load environment variables from apikey.env
load_dotenv(dotenv_path='apikey.env')

# --- Constants ---
USER_DATA_DIR = "UserData"
OUTPUT_DIR = "Results"
PDF_DIR = "UserData/PDFs"

# --- Flask App Initialization ---
app = Flask(__name__)
CORS(app,
     origins=["http://localhost:3000"],
     methods=["GET", "POST", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization"],
     supports_credentials=True)

# --- Utility Functions ---
def ensure_directory_exists(directory):
    os.makedirs(directory, exist_ok=True)

def get_db_connection():
    conn = sqlite3.connect('healthagent.db')
    conn.row_factory = sqlite3.Row  # Allows accessing columns by name
    return conn

def map_stress_level(level):
    if isinstance(level, str):
        return level
    return {1: 'very low', 2: 'low', 3: 'mild', 4: 'moderate', 5: 'moderate',
            6: 'moderate', 7: 'high', 8: 'high', 9: 'very high', 10: 'extreme'}.get(level, 'moderate')

# --- Database Functions ---
def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        age INTEGER NOT NULL,
        gender TEXT NOT NULL,
        phone_number TEXT UNIQUE NOT NULL,
        national_code TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )''')
    
    # Profiles table
    c.execute('''CREATE TABLE IF NOT EXISTS profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        height TEXT, weight TEXT, age INTEGER, primary_goal TEXT, specific_goals TEXT,
        fitness_level TEXT, activity_level TEXT, workout_preference TEXT, workout_days INTEGER,
        workout_duration TEXT, available_equipment TEXT, previous_injuries TEXT, current_injuries TEXT,
        dietary_preferences TEXT, allergies TEXT, food_restrictions TEXT, meals_per_day INTEGER,
        cooking_skill TEXT, budget TEXT, sleep_hours REAL, sleep_quality TEXT, stress_level INTEGER,
        water_intake REAL, smoking_status TEXT, alcohol_consumption TEXT, medications_supplements TEXT,
        chronic_conditions TEXT, bmi TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    
    # Agent history table
    c.execute('''CREATE TABLE IF NOT EXISTS agent_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        agent_type TEXT,
        recommendation TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    
    # 🆕 Chat history table - این خط مهم اضافه شده!
    c.execute('''CREATE TABLE IF NOT EXISTS chat_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        agent_type TEXT,
        thread_id TEXT,
        human_message TEXT,
        ai_response TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully!")

def save_user(first_name, last_name, age, gender, phone_number, national_code, password):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        hashed_password = generate_password_hash(password)
        c.execute("INSERT INTO users (first_name, last_name, age, gender, phone_number, national_code, password) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (first_name, last_name, age, gender, phone_number, national_code, hashed_password))
        conn.commit()
        return c.lastrowid
    except sqlite3.IntegrityError:
        return None  # Indicates that the user already exists
    finally:
        conn.close()

def save_profile(user_id, profile_data):
    conn = get_db_connection()
    c = conn.cursor()
    columns = [
        'user_id', 'height', 'weight', 'age', 'primary_goal', 'specific_goals', 'fitness_level',
        'activity_level', 'workout_preference', 'workout_days', 'workout_duration',
        'available_equipment', 'previous_injuries', 'current_injuries', 'dietary_preferences',
        'allergies', 'food_restrictions', 'meals_per_day', 'cooking_skill', 'budget', 'sleep_hours',
        'sleep_quality', 'stress_level', 'water_intake', 'smoking_status', 'alcohol_consumption',
        'medications_supplements', 'chronic_conditions', 'bmi'
    ]
    values = (
        user_id, profile_data.get('height'), profile_data.get('weight'), profile_data.get('age'),
        profile_data.get('primaryGoal'), profile_data.get('specificGoals'), profile_data.get('fitnessLevel'),
        profile_data.get('activityLevel'), profile_data.get('workoutPreference'), profile_data.get('workoutDays'),
        profile_data.get('workoutDuration'), json.dumps(profile_data.get('availableEquipment', [])),
        profile_data.get('previousInjuries'), profile_data.get('currentInjuries'),
        profile_data.get('dietaryPreferences'), profile_data.get('allergies'),
        profile_data.get('foodRestrictions'), profile_data.get('mealsPerDay'),
        profile_data.get('cookingSkill'), profile_data.get('budget'), profile_data.get('sleepHours'),
        profile_data.get('sleepQuality'), profile_data.get('stressLevel'), profile_data.get('waterIntake'),
        profile_data.get('smokingStatus'), profile_data.get('alcoholConsumption'),
        profile_data.get('medicationsSupplements'), profile_data.get('chronicConditions'),
        profile_data.get('bmi')
    )
    sql = f"INSERT OR REPLACE INTO profiles ({', '.join(columns)}) VALUES ({', '.join(['?'] * len(columns))})"
    c.execute(sql, values)
    conn.commit()
    conn.close()

def authenticate_user(phone_number, national_code, password):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE phone_number = ? AND national_code = ?", (phone_number, national_code))
    result = c.fetchone()
    conn.close()
    return result and check_password_hash(result['password'], password)

def check_profile_exists(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM profiles WHERE user_id = ?", (user_id,))
    return c.fetchone() is not None

def save_history(user_id, agent_type, recommendation):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO agent_history (user_id, agent_type, recommendation) VALUES (?, ?, ?)",
              (user_id, agent_type, recommendation))
    conn.commit()
    conn.close()

# --- Agent-Related Functions ---
# بخش اصلاح شده از تابع get_profile_for_agent در Main.py
def get_profile_for_agent(user_id):
    """Fetches and formats a comprehensive user profile for agent processing."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT u.first_name, p.* FROM users u JOIN profiles p ON u.id = p.user_id WHERE u.id = ?", (user_id,))
    data = c.fetchone()
    conn.close()
    if not data:
        return None
    
    return {
        "name": data['first_name'],
        "age": data['age'],
        "bmi": data['bmi'],
        "goals": data['primary_goal'],
        "specific_goals": data['specific_goals'],
        "duration": 4,
        "fitness_level": data['fitness_level'],
        "workout_preference": data['workout_preference'],
        "equipment": json.loads(data['available_equipment']) if data['available_equipment'] else ['none'],
        "workout_days": data['workout_days'],
        "workout_time": data['workout_duration'],
        "previous_injuries": data['previous_injuries'] or 'none',
        "restrictions": data['current_injuries'] or 'none',
        "diet_preferences": data['dietary_preferences'],
        "food_restrictions": data['food_restrictions'] or 'none',
        "allergies": data['allergies'] or 'none',
        "meals_per_day": data['meals_per_day'],
        "cooking_skill": data['cooking_skill'],
        "budget": data['budget'],
        "caloric_target": 2000,
        "lifestyle": data['activity_level'],
        "sleep_quality": f"{data['sleep_hours']} hours, quality: {data['sleep_quality']}",
        "water_intake_liters": data['water_intake'],  # این خط اصلاح شد
        "stress_level": map_stress_level(data['stress_level']),
        "habits": f"Smoking: {data['smoking_status']}, Alcohol: {data['alcohol_consumption']}",
        "medications_supplements": data['medications_supplements'] or 'none',
        "chronic_conditions": data['chronic_conditions'] or 'none'
    }

def generate_plan(user_data, user_id):
    """Initializes and runs all four agents in parallel."""
    if not user_data:
        return None
    
    agents = {
        "HealthSummary": HealthSummary(user_data),
        "FitnessTrainer": FitnessTrainer(user_data),
        "Nutritionist": Nutritionist(user_data),
        "HealthAdvisor": HealthAdvisor(user_data)
    }
    responses = {}
    with ThreadPoolExecutor() as executor:
        future_to_agent = {executor.submit(agent.run): name for name, agent in agents.items()}
        for future in as_completed(future_to_agent):
            agent_name = future_to_agent[future]
            try:
                response = future.result()
                if response and "Error" not in response:
                    responses[agent_name] = response
                    save_history(user_id, agent_name, response)
                else:
                    responses[agent_name] = f"Failed to generate recommendations for {agent_name}."
            except Exception as exc:
                print(f"❌ {agent_name} generated an exception: {exc}")
                responses[agent_name] = "An unexpected error occurred while generating this plan."
    return responses

# --- API Endpoints ---
def handle_errors(f):
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            print(f"Error in {f.__name__}: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    wrapper.__name__ = f.__name__
    return wrapper

@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        return jsonify(success=True)

@app.route('/api/signup', methods=['POST'])
@handle_errors
def signup():
    data = request.get_json()
    required_fields = ['firstName', 'lastName', 'age', 'gender', 'phoneNumber', 'nationalCode', 'password']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400

    user_id = save_user(
        data['firstName'], data['lastName'], int(data['age']), data['gender'],
        data['phoneNumber'], data['nationalCode'], data['password']
    )
    if user_id:
        return jsonify({'message': 'User created successfully!', 'user_id': user_id}), 201
    else:
        return jsonify({'error': 'Phone number or national code already exists'}), 409

@app.route('/api/login', methods=['POST'])
@handle_errors
def login():
    data = request.get_json()
    if not all(k in data for k in ['phoneNumber', 'nationalCode', 'password']):
        return jsonify({'error': 'Missing required fields'}), 400

    if authenticate_user(data['phoneNumber'], data['nationalCode'], data['password']):
        conn = get_db_connection()
        user = conn.execute("SELECT id, first_name FROM users WHERE phone_number = ?", (data['phoneNumber'],)).fetchone()
        conn.close()
        
        has_profile = check_profile_exists(user['id'])
        
        return jsonify({
            'message': f'Welcome back, {user["first_name"]}!',
            'user_id': user['id'],
            'first_name': user['first_name'],
            'has_profile': has_profile
        }), 200
    else:
        return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/profile', methods=['POST'])
@handle_errors
def save_profile_api():
    user_id = request.form.get('user_id')
    if not user_id:
        return jsonify({'error': 'Missing user_id'}), 400
    
    profile_data = {key: request.form[key] for key in request.form}
    if 'availableEquipment' in profile_data:
        profile_data['availableEquipment'] = json.loads(profile_data['availableEquipment'])

    save_profile(int(user_id), profile_data)
    return jsonify({'message': 'Profile saved successfully!'}), 200

@app.route('/api/generate-plan', methods=['POST'])
@handle_errors
def generate_plan_api():
    data = request.get_json()
    user_id = data.get('userId')
    if not user_id:
        return jsonify({'error': 'userId is required'}), 400

    user_profile = get_profile_for_agent(user_id)
    if not user_profile:
        return jsonify({'error': 'Profile not found for this user.'}), 404
        
    plans = generate_plan(user_profile, user_id)
    if not plans:
        return jsonify({'error': 'Failed to generate plans.'}), 500

    return jsonify(plans), 200

@app.route('/api/get-history', methods=['POST'])
@handle_errors
def get_history_api():
    data = request.get_json()
    user_id = data.get('userId')
    if not user_id:
        return jsonify({'error': 'userId is required'}), 400

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        SELECT agent_type, recommendation FROM agent_history
        WHERE id IN (SELECT MAX(id) FROM agent_history WHERE user_id = ? GROUP BY agent_type)
    """, (user_id,))
    history = c.fetchall()
    conn.close()
    
    plans = {row['agent_type']: row['recommendation'] for row in history}
    return jsonify(plans), 200

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()}), 200

# Replace your existing chat endpoints with these debug versions

@app.route('/api/chat', methods=['POST'])
@handle_errors
def chat_endpoint():
    """Handle chat messages"""
    try:
        data = request.get_json()
        print(f"🔍 Chat request data: {data}")  # Debug line
        
        # Validate required fields
        required_fields = ['userId', 'agentType', 'message', 'threadId']
        if not all(field in data for field in required_fields):
            print(f"❌ Missing required fields")  # Debug line
            return jsonify({'error': 'Missing required fields'}), 400
        
        user_id = data['userId']
        agent_type = data['agentType']
        message = data['message'].strip()
        thread_id = data['threadId']
        
        print(f"🔍 Processing chat for user {user_id}, agent {agent_type}")  # Debug line
        
        # Validate agent type
        valid_agents = ['HealthSummary', 'FitnessTrainer', 'Nutritionist', 'HealthAdvisor']
        if agent_type not in valid_agents:
            return jsonify({'error': 'Invalid agent type'}), 400
        
        # Validate message
        if not message or len(message) > 1000:
            return jsonify({'error': 'Message must be between 1-1000 characters'}), 400
        
        # Generate response using chat manager
        result = chat_manager.generate_response(user_id, agent_type, message, thread_id)
        print(f"✅ Chat response generated successfully")  # Debug line
        
        if result['success']:
            return jsonify({
                'success': True,
                'response': result['response']
            }), 200
        else:
            print(f"❌ Chat generation failed: {result['error']}")  # Debug line
            return jsonify({
                'success': False,
                'error': result['error']
            }), 500
            
    except Exception as e:
        print(f"❌ Chat endpoint error: {str(e)}")  # Debug line
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@app.route('/api/chat-history', methods=['POST'])
@handle_errors
def get_chat_history():
    """Get chat history for a user and agent"""
    try:
        data = request.get_json()
        print(f"🔍 Chat history request data: {data}")  # Debug line
        
        if not all(k in data for k in ['userId', 'agentType']):
            print(f"❌ Missing userId or agentType")  # Debug line
            return jsonify({'error': 'Missing userId or agentType'}), 400
        
        user_id = data['userId']
        agent_type = data['agentType']
        limit = data.get('limit', 20)
        
        print(f"🔍 Processing chat history for user {user_id}, agent {agent_type}")  # Debug line
        
        # Validate agent type
        valid_agents = ['HealthSummary', 'FitnessTrainer', 'Nutritionist', 'HealthAdvisor']
        if agent_type not in valid_agents:
            return jsonify({'error': 'Invalid agent type'}), 400
        
        history = chat_manager.get_chat_history(user_id, agent_type, limit)
        print(f"✅ Chat history retrieved: {len(history)} messages")  # Debug line
        
        return jsonify({
            'success': True,
            'history': history
        }), 200
        
    except Exception as e:
        print(f"❌ Chat history error: {str(e)}")  # Debug line
        import traceback
        traceback.print_exc()  # Print full stack trace
        return jsonify({
            'success': False,
            'error': f'Failed to get chat history: {str(e)}'
        }), 500

@app.route('/api/clear-chat', methods=['POST'])
@handle_errors
def clear_chat_history():
    """Clear chat history for a user and agent"""
    try:
        data = request.get_json()
        print(f"🔍 Clear chat request data: {data}")  # Debug line
        
        if not all(k in data for k in ['userId', 'agentType']):
            return jsonify({'error': 'Missing userId or agentType'}), 400
        
        user_id = data['userId']
        agent_type = data['agentType']
        
        print(f"🔍 Clearing chat history for user {user_id}, agent {agent_type}")  # Debug line
        
        # Validate agent type
        valid_agents = ['HealthSummary', 'FitnessTrainer', 'Nutritionist', 'HealthAdvisor']
        if agent_type not in valid_agents:
            return jsonify({'error': 'Invalid agent type'}), 400
        
        chat_manager.clear_chat_history(user_id, agent_type)
        print(f"✅ Chat history cleared successfully")  # Debug line
        
        return jsonify({
            'success': True,
            'message': 'Chat history cleared successfully'
        }), 200
        
    except Exception as e:
        print(f"❌ Clear chat error: {str(e)}")  # Debug line
        return jsonify({
            'success': False,
            'error': f'Failed to clear chat history: {str(e)}'
        }), 500

# اضافه کردن این endpoints به فایل Main.py

@app.route('/api/get-current-plans', methods=['POST'])
@handle_errors
def get_current_plans_api():
    """Get current plans (updated or original) for display"""
    data = request.get_json()
    user_id = data.get('userId')
    if not user_id:
        return jsonify({'error': 'userId is required'}), 400

    try:
        from Utils.ChatAgent import chat_manager
        
        agent_types = ['HealthSummary', 'FitnessTrainer', 'Nutritionist', 'HealthAdvisor']
        current_plans = {}
        
        for agent_type in agent_types:
            plan_info = chat_manager.get_current_plan(user_id, agent_type)
            current_plans[agent_type] = {
                'content': plan_info['plan'],
                'is_updated': plan_info['is_updated'],
                'modifications': plan_info['modifications']
            }
        
        return jsonify(current_plans), 200
        
    except Exception as e:
        print(f"❌ Error getting current plans: {str(e)}")
        return jsonify({'error': 'Failed to get current plans'}), 500

@app.route('/api/plan-updates-history', methods=['POST'])
@handle_errors
def get_plan_updates_history():
    """Get history of plan updates"""
    data = request.get_json()
    user_id = data.get('userId')
    agent_type = data.get('agentType')
    
    if not user_id or not agent_type:
        return jsonify({'error': 'userId and agentType are required'}), 400

    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""
            SELECT modification_summary, created_at, updated_plan
            FROM updated_plans
            WHERE user_id = ? AND agent_type = ?
            ORDER BY created_at DESC
            LIMIT 10
        """, (user_id, agent_type))
        
        updates = []
        for row in c.fetchall():
            updates.append({
                'summary': row['modification_summary'],
                'timestamp': row['created_at'],
                'preview': row['updated_plan'][:200] + '...' if len(row['updated_plan']) > 200 else row['updated_plan']
            })
        
        conn.close()
        return jsonify({'updates': updates}), 200
        
    except Exception as e:
        print(f"❌ Error getting plan updates history: {str(e)}")
        return jsonify({'error': 'Failed to get updates history'}), 500

@app.route('/api/reset-to-original', methods=['POST'])
@handle_errors
def reset_to_original_plan():
    """Reset agent plan to original version"""
    data = request.get_json()
    user_id = data.get('userId')
    agent_type = data.get('agentType')
    
    if not user_id or not agent_type:
        return jsonify({'error': 'userId and agentType are required'}), 400

    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Delete all updated plans for this user and agent
        c.execute("""
            DELETE FROM updated_plans
            WHERE user_id = ? AND agent_type = ?
        """, (user_id, agent_type))
        
        # Also clear chat history to start fresh
        c.execute("""
            DELETE FROM chat_history
            WHERE user_id = ? AND agent_type = ?
        """, (user_id, agent_type))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Plan reset to original version successfully'}), 200
        
    except Exception as e:
        print(f"❌ Error resetting plan: {str(e)}")
        return jsonify({'error': 'Failed to reset plan'}), 500
        
# --- Main Execution ---
if __name__ == "__main__":
    ensure_directory_exists(USER_DATA_DIR)
    ensure_directory_exists(OUTPUT_DIR)
    ensure_directory_exists(PDF_DIR)
    init_db()
    print("🚀 Starting HealthAgent Server...")
    print("📡 Listening on http://127.0.0.1:5000")
    app.run(debug=True, port=5000, host='127.0.0.1')

