import os
import json
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', 'apikey.env'))

class Agent:
    def __init__(self, user_data=None, role=None):
        self.user_data = user_data or {}
        self.role = role
        self.prompt_template = self.create_prompt_template()
        try:
            self.model = ChatOpenAI(
                temperature=0.7,
                model="google/gemma-3-12b-it:free",
                base_url="https://openrouter.ai/api/v1",
                api_key=os.getenv("OPENROUTER_API_KEY"),
                max_retries=3,
                timeout=120
            )
        except Exception as e:
            print(f"Error initializing LLM for role {self.role}: {str(e)}")
            raise

    def create_prompt_template(self):
        """Creates a balanced and directive PromptTemplate for each agent's role."""
        templates = {
            "HealthSummary": """
You are a professional health data analyst. Your task is to generate a "Current Health Snapshot" for {name}.
Please use only the detailed profile data provided below to construct your analysis. Your response should be direct and structured as requested.

### Client Profile Data
- **Age**: {age}
- **BMI**: {bmi}
- **Primary Goal**: {goals}
- **Specific Goals**: {specific_goals}
- **Fitness Level**: {fitness_level}
- **Activity Level**: {lifestyle}
- **Health Conditions**: {chronic_conditions}
- **Medications/Supplements**: {medications_supplements}

### Output Requirements
Your entire response should follow this structure:
1.  **Overall Summary**: A short, encouraging paragraph.
2.  **Key Strengths**: 2-3 bullet points on positive aspects.
3.  **Areas for Focus**: 2-3 bullet points on areas for improvement.
""",
            "FitnessTrainer": """
You are an expert personal trainer acting as a plan generator. Your task is to create a complete, personalized {duration}-week workout plan for {name}.
Generate the plan directly using only the comprehensive client data below. The response should be the full plan itself.

### Client Profile Data
- **Primary Goal**: {goals}, specifically: {specific_goals}
- **Fitness Level**: {fitness_level}
- **Workout Preference**: {workout_preference}
- **Available Equipment**: {equipment}
- **Workout Schedule**: {workout_days} days/week, for {workout_time} per session.
- **Health & Injury History**:
  - **Previous Injuries**: {previous_injuries}
  - **Current Restrictions**: {restrictions}
  - **Chronic Conditions**: {chronic_conditions}

### Output Requirements
Please generate a complete plan with the following sections using Markdown:
1.  **Weekly Schedule**: A table for workout/rest days.
2.  **Detailed Warm-up & Cool-down Routines**.
3.  **Daily Workout Breakdown**: Exercises with sets, reps, and rest.
4.  **Progression Plan**: How to advance over {duration} weeks.
5.  **Safety Notes**: Important advice regarding their injuries.
""",
            "Nutritionist": """
You are a professional nutritionist. Your job is to design a detailed {duration}-week meal plan for {name}.
Please create the entire plan based exclusively on the detailed client profile provided. Your output should be the plan itself.

### Client Profile Data
- **Primary Goal**: {goals}, specifically: {specific_goals}
- **Dietary Info**:
  - **Preferences**: {diet_preferences}
  - **Restrictions/Dislikes**: {food_restrictions}
  - **Allergies**: {allergies}
- **Lifestyle & Habits**:
  - **Meals Per Day**: {meals_per_day}
  - **Cooking Skill**: {cooking_skill}
  - **Food Budget**: {budget}
  - **Daily Water Intake**: {water_intake_liters} Liters
- **Caloric Target**: Approx. {caloric_target} Kcal

### Output Requirements
Please provide a full meal plan structured as follows:
1.  **Nutritional Strategy**: A brief explanation.
2.  **Sample Full Day of Eating**: A detailed one-day example.
3.  **Weekly Meal Ideas**: A variety of options.
4.  **Grocery List**: A sample weekly list.
5.  **Practical Tips**: Advice on hydration and meal prep.
""",
            "HealthAdvisor": """
You are a compassionate health advisor. Please provide a list of actionable wellness recommendations for {name}.
Base your advice directly on the client's information below. The response should be the advice itself.

### Client Profile Data
- **Primary Goal**: {goals}
- **Lifestyle**: {lifestyle}
- **Health Context**:
  - **Sleep Habits**: {sleep_quality}
  - **Stress Level**: {stress_level}
  - **Reported Habits**: {habits}
  - **Medications/Supplements**: {medications_supplements}
  - **Chronic Conditions**: {chronic_conditions}

### Output Requirements
Please structure your advice in these sections:
1.  **Sleep Enhancement Strategy**: Actionable tips for sleep.
2.  **Stress Management Techniques**: Simple techniques for stress.
3.  **Habit Optimization**: Constructive advice on their habits.
4.  **General Wellness**: Advice considering their health conditions.
5.  **Mindset and Motivation**: Tips to stay motivated.
"""
        }
        return PromptTemplate.from_template(templates[self.role])

    def run(self):
        # This function remains unchanged as it correctly passes all parameters.
        print(f"[{self.role}] is formatting the prompt...")
        try:
            prompt_params = {key: self.user_data.get(key, 'N/A') for key in [
                'name', 'age', 'bmi', 'goals', 'specific_goals', 'duration', 'fitness_level',
                'workout_preference', 'equipment', 'workout_days', 'workout_time',
                'previous_injuries', 'restrictions', 'diet_preferences', 'food_restrictions',
                'allergies', 'meals_per_day', 'cooking_skill', 'budget', 'caloric_target',
                'lifestyle', 'sleep_quality', 'water_intake_liters', 'stress_level',
                'habits', 'medications_supplements', 'chronic_conditions'
            ]}
            prompt = self.prompt_template.format(**prompt_params)
            response = self.model.invoke(prompt)
            if not response or not response.content.strip():
                raise ValueError("Received an empty or blank response from the model.")
            return response.content
        except Exception as e:
            error_msg = f"An error occurred in [{self.role}]: {str(e)}"
            print(error_msg)
            return error_msg

# --- Specialized Agent Classes ---
class HealthSummary(Agent):
    def __init__(self, user_data): super().__init__(user_data, "HealthSummary")
class FitnessTrainer(Agent):
    def __init__(self, user_data): super().__init__(user_data, "FitnessTrainer")
class Nutritionist(Agent):
    def __init__(self, user_data): super().__init__(user_data, "Nutritionist")
class HealthAdvisor(Agent):
    def __init__(self, user_data): super().__init__(user_data, "HealthAdvisor")