import os
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from Utils.Agents import FitnessTrainer, Nutritionist, HealthAdvisor

# Load environment variables
load_dotenv(dotenv_path='apikey.env')

# Constants
USER_DATA_DIR = "UserData"
SAMPLE_USER_FILE = "sample_user_profile.txt"
OUTPUT_DIR = "Results"

def ensure_directory_exists(directory):
    """Create directory if it doesn't exist"""
    os.makedirs(directory, exist_ok=True)

def validate_user_data(raw_data):
    """Validate the structure of user data"""
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
    """Convert raw user data into agent-friendly format with validation"""
    try:
        validate_user_data(raw_data)
        
        return {
            # Shared fields
            "name": raw_data['profile']['name'],
            "goals": raw_data['profile']['goals'],
            "duration": 4,  # Default 4-week plan
            
            # Fitness
            "fitness_level": raw_data['fitness'].get('level', 'beginner'),
            "equipment": raw_data['fitness'].get('equipment', 'none'),
            "workout_days": raw_data['fitness'].get('days_per_week', 3),
            "workout_time": raw_data['fitness'].get('session_minutes', 30),
            "restrictions": raw_data['fitness'].get('injuries', 'none'),
            
            # Nutrition
            "diet_preferences": raw_data['nutrition'].get('preferences', 'balanced'),
            "allergies": raw_data['nutrition'].get('allergies', 'none'),
            "caloric_target": raw_data['nutrition'].get('target_calories', 2000),
            "lifestyle": raw_data['profile'].get('activity', 'moderately active'),
            
            # Health
            "sleep_quality": f"{raw_data['health'].get('sleep_hours', 7)} hours",
            "stress_level": map_stress_level(raw_data['health'].get('stress_level', 5)),
            "habits": raw_data['health'].get('habits', 'none reported')
        }
    except Exception as e:
        print(f"Error processing user data: {str(e)}")
        return None

def map_stress_level(level):
    """Convert numeric stress level to descriptive term"""
    if isinstance(level, str):
        return level
    return {
        1: 'very low', 2: 'low', 3: 'mild', 
        4: 'moderate', 5: 'moderate', 6: 'moderate',
        7: 'high', 8: 'high', 9: 'very high', 10: 'extreme'
    }.get(level, 'moderate')

def generate_plan(user_data, output_dir):
    """Run all agents and save individual outputs"""
    if not user_data:
        print("❌ No valid user data provided")
        return None

    agents = {
        "FitnessTrainer": FitnessTrainer(user_data),
        "Nutritionist": Nutritionist(user_data),
        "HealthAdvisor": HealthAdvisor(user_data)
    }

    # Run agents concurrently
    responses = {}
    with ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(lambda a: (name, a.run()), agent): name 
            for name, agent in agents.items()
        }
        
        for future in as_completed(futures):
            agent_name, response = future.result()
            if response and "Error" not in response:
                responses[agent_name] = response
                print(f"✅ {agent_name} recommendations complete")
            else:
                print(f"❌ {agent_name} failed: {response}")

    # Save individual outputs
    ensure_directory_exists(output_dir)
    user_id = user_data.get('name', 'user').replace(' ', '_').lower()
    
    for agent_name, content in responses.items():
        output_path = f"{output_dir}/{user_id}_{agent_name.lower()}_plan.txt"
        with open(output_path, 'w') as file:
            file.write(f"=== {agent_name.upper()} RECOMMENDATIONS ===\n\n")
            file.write(f"User: {user_data.get('name', 'User')}\n")
            file.write(f"Goals: {user_data.get('goals', 'General wellness')}\n\n")
            file.write(content)
        print(f"📄 Saved {agent_name} plan to {output_path}")

    return responses

def main():
    # Set up directories
    ensure_directory_exists(USER_DATA_DIR)
    ensure_directory_exists(OUTPUT_DIR)
    
    # Load user data
    user_file = os.path.join(USER_DATA_DIR, SAMPLE_USER_FILE)
    
    try:
        with open(user_file, 'r') as f:
            raw_data = json.load(f)
    except Exception as e:
        print(f"❌ Error loading user data: {str(e)}")
        return
    
    processed_data = process_user_data(raw_data)
    if not processed_data:
        return
    
    # Generate and save plans
    generate_plan(processed_data, OUTPUT_DIR)

if __name__ == "__main__":
    main()