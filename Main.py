import os
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from Utils.Agents import FitnessTrainer, Nutritionist, HealthAdvisor
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# Load environment variables
load_dotenv(dotenv_path='apikey.env')

# Constants
USER_DATA_DIR = "UserData"
SAMPLE_USER_FILE = "sample_user_profile.txt"
OUTPUT_DIR = "Results"

def ensure_directory_exists(directory):
    os.makedirs(directory, exist_ok=True)

def validate_user_data(raw_data):
    required = {
        'profile': ['name', 'goals'],
        'fitness': ['level'],
        'nutrition': ['preferences'],
        'health': ['sleep_hours']
    }
    for section, fields in required.items():
        if section not in raw_data:
            raise ValueError(f"Missing section: {section}")
        for field in fields:
            if field not in raw_data[section]:
                raise ValueError(f"Missing field: {section}.{field}")

def process_user_data(raw_data):
    try:
        validate_user_data(raw_data)
        return {
            "name": raw_data['profile']['name'],
            "goals": raw_data['profile']['goals'],
            "duration": 4,
            "fitness_level": raw_data['fitness'].get('level', 'beginner'),
            "equipment": raw_data['fitness'].get('equipment', 'none'),
            "workout_days": raw_data['fitness'].get('days_per_week', 3),
            "workout_time": raw_data['fitness'].get('session_minutes', 30),
            "restrictions": raw_data['fitness'].get('injuries', 'none'),
            "diet_preferences": raw_data['nutrition'].get('preferences', 'balanced'),
            "allergies": raw_data['nutrition'].get('allergies', 'none'),
            "caloric_target": raw_data['nutrition'].get('target_calories', 2000),
            "lifestyle": raw_data['profile'].get('activity', 'moderately active'),
            "sleep_quality": f"{raw_data['health'].get('sleep_hours', 7)} hours",
            "stress_level": map_stress_level(raw_data['health'].get('stress_level', 5)),
            "habits": raw_data['health'].get('habits', 'none reported')
        }
    except Exception as e:
        print(f"Error processing user data: {str(e)}")
        return None

def map_stress_level(level):
    if isinstance(level, str):
        return level
    return {1: 'very low', 2: 'low', 3: 'mild', 4: 'moderate', 5: 'moderate',
            6: 'moderate', 7: 'high', 8: 'high', 9: 'very high', 10: 'extreme'}.get(level, 'moderate')

def get_db_connection():
    conn = sqlite3.connect('healthagent.db')
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS agent_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        agent_type TEXT,
        recommendation TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    conn.commit()
    conn.close()

def save_user(username, password):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        hashed_password = generate_password_hash(password)
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        print(f"Username '{username}' already exists")
        return False
    finally:
        conn.close()

def authenticate_user(username, password):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT password FROM users WHERE username = ?", (username,))
        result = c.fetchone()
        if result and check_password_hash(result[0], password):
            return True
        return False
    finally:
        conn.close()

def save_history(user_id, agent_type, recommendation):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO agent_history (user_id, agent_type, recommendation) VALUES (?, ?, ?)",
                  (user_id, agent_type, recommendation))
        conn.commit()
    except Exception as e:
        print(f"Error saving history: {str(e)}")
    finally:
        conn.close()

def generate_plan(user_data, user_id):
    if not user_data:
        print("❌ No valid user data provided")
        return None

    agents = {
        "FitnessTrainer": FitnessTrainer(user_data),
        "Nutritionist": Nutritionist(user_data),
        "HealthAdvisor": HealthAdvisor(user_data)
    }

    responses = {}
    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(lambda a: (name, a.run()), agent): name for name, agent in agents.items()}
        for future in as_completed(futures):
            agent_name, response = future.result()
            if response and "Error" not in response:
                responses[agent_name] = response
                save_history(user_id, agent_name, response)
                print(f"✅ {agent_name} recommendations complete")
            else:
                print(f"❌ {agent_name} failed: {response}")

    ensure_directory_exists(OUTPUT_DIR)
    user_id_str = str(user_id)
    for agent_name, content in responses.items():
        output_path = f"{OUTPUT_DIR}/{user_id_str}_{agent_name.lower()}_plan.txt"
        with open(output_path, 'w') as file:
            file.write(f"=== {agent_name.upper()} RECOMMENDATIONS ===\n\n")
            file.write(f"User: {user_data.get('name', 'User')}\n")
            file.write(f"Goals: {user_data.get('goals', 'General wellness')}\n\n")
            file.write(content)
        print(f"📄 Saved {agent_name} plan to {output_path}")

    return responses

def main():
    ensure_directory_exists(USER_DATA_DIR)
    ensure_directory_exists(OUTPUT_DIR)

    # Initialize database
    init_db()

    while True:
        action = input("Choose action (signup/login/exit): ").lower()
        if action == 'exit':
            break
        elif action == 'signup':
            username = input("Enter username: ")
            password = input("Enter password: ")
            if save_user(username, password):
                print(f"User '{username}' created successfully")
            else:
                print(f"Failed to create user '{username}'")
        elif action == 'login':
            username = input("Enter username: ")
            password = input("Enter password: ")
            if authenticate_user(username, password):
                user_id = 1  # Dummy user_id for now (will link to DB later)
                
                user_file = os.path.join(USER_DATA_DIR, SAMPLE_USER_FILE)
                try:
                    with open(user_file, 'r') as f:
                        raw_data = json.load(f)
                except Exception as e:
                    print(f"❌ Error loading user data: {str(e)}")
                    continue

                processed_data = process_user_data(raw_data)
                if not processed_data:
                    continue

                generate_plan(processed_data, user_id)
                break
            else:
                print("❌ Invalid credentials")
        else:
            print("Invalid action. Choose signup, login, or exit.")

if __name__ == "__main__":
    main()