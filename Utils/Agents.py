from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os
import json

# Load environment variables from apikey.env in root
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', 'apikey.env'))

class Agent:
    def __init__(self, user_data=None, role=None):
        # Initialize with default empty dict if no data provided
        self.user_data = user_data or {}
        self.role = role
        self.prompt_template = self.create_prompt_template()
        
        # Configure the LLM model with error handling
        try:
            self.model = ChatOpenAI(
                temperature=0.7,
                model="google/gemma-3-27b-it:free",
                base_url="https://openrouter.ai/api/v1",
                api_key=os.getenv("OPENROUTER_API_KEY"),
                max_retries=3,
                timeout=60
            )
        except Exception as e:
            print(f"Error initializing model for {role}: {str(e)}")
            raise

    def create_prompt_template(self):
        """Define prompt templates for each agent role"""
        templates = {
            "FitnessTrainer": """
                As a professional fitness trainer, create a personalized {duration}-week workout plan for {name}.

                Client Profile:
                - Goals: {goals}
                - Fitness Level: {fitness_level}
                - Available Equipment: {equipment}
                - Workout Frequency: {workout_days} days/week
                - Session Duration: {workout_time} minutes
                - Restrictions: {restrictions}

                Required Output:
                1. Warm-up routine (5-10 minutes)
                2. Main exercises (include sets/reps/rest periods)
                3. Cool-down stretches
                4. Progression plan for {duration} weeks
                5. Safety modifications for {restrictions}
            """,
            "Nutritionist": """
                As a certified nutritionist, create a {duration}-week meal plan for {name}.

                Client Profile:
                - Goals: {goals}
                - Dietary Preferences: {diet_preferences}
                - Allergies: {allergies}
                - Daily Caloric Target: {caloric_target}
                - Lifestyle: {lifestyle}

                Required Output:
                1. Daily meal breakdown (breakfast, lunch, dinner, snacks)
                2. Macronutrient distribution
                3. Weekly grocery list
                4. Meal prep tips
                5. Hydration guidelines
            """,
            "HealthAdvisor": """
                As a holistic health advisor, provide wellness recommendations for {name}.

                Client Profile:
                - Goals: {goals}
                - Sleep Quality: {sleep_quality}
                - Stress Level: {stress_level}
                - Habits: {habits}
                - Lifestyle: {lifestyle}

                Required Output:
                1. Sleep improvement strategies
                2. Stress management techniques
                3. Habit optimization suggestions
                4. Daily routine recommendations
                5. Preventative health measures
            """
        }
        return PromptTemplate.from_template(templates[self.role])
    
    def run(self):
        """Execute the agent's analysis and return recommendations"""
        print(f"{self.role} is generating recommendations...")
        try:
            # Validate required fields
            if not self.user_data.get('name'):
                raise ValueError("Missing user name")
            if not self.user_data.get('goals'):
                raise ValueError("Missing user goals")

            # Format prompt with safe defaults
            prompt_params = {
                'name': self.user_data.get('name', 'Client'),
                'goals': self.user_data.get('goals', 'general wellness'),
                'duration': self.user_data.get('duration', 4),
                'fitness_level': self.user_data.get('fitness_level', 'beginner'),
                'equipment': self.user_data.get('equipment', 'none'),
                'workout_days': self.user_data.get('workout_days', 3),
                'workout_time': self.user_data.get('workout_time', 30),
                'restrictions': self.user_data.get('restrictions', 'none'),
                'diet_preferences': self.user_data.get('diet_preferences', 'balanced'),
                'allergies': self.user_data.get('allergies', 'none'),
                'caloric_target': self.user_data.get('caloric_target', 2000),
                'lifestyle': self.user_data.get('lifestyle', 'moderately active'),
                'sleep_quality': self.user_data.get('sleep_quality', '7 hours'),
                'stress_level': self.user_data.get('stress_level', 'moderate'),
                'habits': self.user_data.get('habits', 'none reported')
            }

            prompt = self.prompt_template.format(**prompt_params)
            response = self.model.invoke(prompt)
            
            if not response or not response.content:
                raise ValueError("Empty response from model")
                
            return response.content
            
        except Exception as e:
            error_msg = f"{self.role} Error: {str(e)}"
            print(error_msg)
            return error_msg

# Specialized Agent Classes
class FitnessTrainer(Agent):
    def __init__(self, user_data):
        super().__init__(user_data, "FitnessTrainer")

class Nutritionist(Agent):
    def __init__(self, user_data):
        super().__init__(user_data, "Nutritionist")

class HealthAdvisor(Agent):
    def __init__(self, user_data):
        super().__init__(user_data, "HealthAdvisor")