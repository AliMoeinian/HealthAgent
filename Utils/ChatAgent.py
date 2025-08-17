import os
import json
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', 'apikey.env'))


class ChatManager:
    def __init__(self):
        self.db_path = 'healthagent.db'
        self.init_chat_db()

        # Initialize LLM با استفاده از environment variable
        try:
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                raise ValueError("OPENROUTER_API_KEY not found in environment variables")
                
            self.model = ChatOpenAI(
                temperature=0.7,
                model="google/gemma-3-12b-it:free",
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key,
                max_retries=3,
                timeout=120
            )
            print("✅ ChatManager LLM initialized successfully")
        except Exception as e:
            print(f"❌ Error initializing ChatManager LLM: {str(e)}")
            raise

    def init_chat_db(self):
        """Initialize database with enhanced schema"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Create chat_history table
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
        
        # Create updated_plans table for tracking plan modifications
        c.execute('''CREATE TABLE IF NOT EXISTS updated_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            agent_type TEXT,
            original_plan TEXT,
            updated_plan TEXT,
            modification_summary TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )''')
        
        conn.commit()
        conn.close()
        print("✅ Chat database tables initialized")

    def get_user_context(self, user_id):
        """اطلاعات کاربر را از دیتابیس دریافت می‌کند"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        try:
            # ابتدا اطلاعات کاربر را دریافت کنیم
            c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            user_data = c.fetchone()
            
            if not user_data:
                print(f"❌ User with ID {user_id} not found")
                return {}

            # سپس اطلاعات پروفایل را دریافت کنیم
            c.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,))
            profile_data = c.fetchone()
            
            if not profile_data:
                print(f"⚠️ Profile for user {user_id} not found")
                # اگر پروفایل وجود نداشت، حداقل اطلاعات کاربر را برگردان
                return {
                    'name': user_data['first_name'],
                    'age': user_data['age'],
                    'weight': 'Unknown',
                    'height': 'Unknown',
                    'bmi': 'Unknown',
                    'goals': 'Unknown',
                    'specific_goals': 'Unknown',
                    'lifestyle': 'Unknown',
                    'fitness_level': 'Unknown',
                    'workout_preference': 'Unknown',
                    'equipment': ['None'],
                    'workout_days': 'Unknown',
                    'workout_time': 'Unknown',
                    'previous_injuries': 'None',
                    'diet_preferences': 'Unknown',
                    'allergies': 'None',
                    'food_restrictions': 'None',
                    'meals_per_day': 'Unknown',
                    'cooking_skill': 'Unknown',
                    'budget': 'Unknown',
                    'sleep_quality': 'Unknown',
                    'stress_level': 'Unknown',
                    'habits': 'Unknown',
                    'medications_supplements': 'None',
                    'chronic_conditions': 'None',
                    'water_intake_liters': 'Unknown',
                    'restrictions': 'None'
                }

            # پردازش equipment
            equipment = []
            if profile_data['available_equipment']:
                try:
                    equipment = json.loads(profile_data['available_equipment'])
                except:
                    equipment = ['None']
            else:
                equipment = ['None']

            # ایجاد context کامل
            context = {
                'name': user_data['first_name'],
                'age': profile_data['age'] or user_data['age'] or 'Unknown',
                'weight': profile_data['weight'] or 'Unknown',
                'height': profile_data['height'] or 'Unknown',
                'bmi': profile_data['bmi'] or 'Unknown',
                'goals': profile_data['primary_goal'] or 'Unknown',
                'specific_goals': profile_data['specific_goals'] or 'Unknown',
                'lifestyle': profile_data['activity_level'] or 'Unknown',
                'fitness_level': profile_data['fitness_level'] or 'Unknown',
                'workout_preference': profile_data['workout_preference'] or 'Unknown',
                'equipment': equipment,
                'workout_days': profile_data['workout_days'] or 'Unknown',
                'workout_time': profile_data['workout_duration'] or 'Unknown',
                'previous_injuries': profile_data['previous_injuries'] or 'None',
                'restrictions': profile_data['current_injuries'] or 'None',
                'diet_preferences': profile_data['dietary_preferences'] or 'Unknown',
                'allergies': profile_data['allergies'] or 'None',
                'food_restrictions': profile_data['food_restrictions'] or 'None',
                'meals_per_day': profile_data['meals_per_day'] or 'Unknown',
                'cooking_skill': profile_data['cooking_skill'] or 'Unknown',
                'budget': profile_data['budget'] or 'Unknown',
                'sleep_quality': f"{profile_data['sleep_hours']} hours, quality: {profile_data['sleep_quality']}" 
                                if profile_data['sleep_hours'] and profile_data['sleep_quality'] 
                                else 'Unknown',
                'stress_level': self.map_stress_level(profile_data['stress_level']) 
                               if profile_data['stress_level'] else 'Unknown',
                'habits': f"Smoking: {profile_data['smoking_status']}, Alcohol: {profile_data['alcohol_consumption']}"
                          if profile_data['smoking_status'] and profile_data['alcohol_consumption'] else 'Unknown',
                'medications_supplements': profile_data['medications_supplements'] or 'None',
                'chronic_conditions': profile_data['chronic_conditions'] or 'None',
                'water_intake_liters': profile_data['water_intake'] or 'Unknown'
            }

            print(f"✅ User context loaded successfully for user {user_id}")
            return context

        except Exception as e:
            print(f"❌ Error getting user context for user {user_id}: {str(e)}")
            return {}
        finally:
            conn.close()

    def map_stress_level(self, level):
        """سطح استرس را از عدد به متن تبدیل می‌کند"""
        if isinstance(level, str):
            return level
        return {
            1: 'very low', 2: 'low', 3: 'mild', 4: 'moderate', 5: 'moderate',
            6: 'moderate', 7: 'high', 8: 'high', 9: 'very high', 10: 'extreme'
        }.get(level, 'moderate')

    def get_current_plan(self, user_id, agent_type):
        """Get the most current plan (either updated or original)"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        try:
            # First check for updated plans
            c.execute("""
                SELECT updated_plan, modification_summary FROM updated_plans
                WHERE user_id = ? AND agent_type = ?
                ORDER BY created_at DESC LIMIT 1
            """, (user_id, agent_type))
            updated_result = c.fetchone()
            
            if updated_result:
                print(f"✅ Found updated plan for user {user_id}, agent {agent_type}")
                return {
                    'plan': updated_result[0],
                    'modifications': updated_result[1],
                    'is_updated': True
                }
            
            # If no updated plan, get original
            c.execute("""
                SELECT recommendation FROM agent_history
                WHERE user_id = ? AND agent_type = ?
                ORDER BY created_at DESC LIMIT 1
            """, (user_id, agent_type))
            original_result = c.fetchone()
            
            if original_result:
                print(f"✅ Found original plan for user {user_id}, agent {agent_type}")
                return {
                    'plan': original_result[0],
                    'modifications': None,
                    'is_updated': False
                }
            
            return {
                'plan': "No previous recommendations found. I'm here to help create a personalized plan for you!",
                'modifications': None,
                'is_updated': False
            }
            
        except Exception as e:
            print(f"❌ Error getting current plan: {str(e)}")
            return {
                'plan': "I'm here to help with your health and wellness questions!",
                'modifications': None,
                'is_updated': False
            }
        finally:
            conn.close()

    def save_updated_plan(self, user_id, agent_type, original_plan, updated_plan, modification_summary):
        """Save an updated plan to the database"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        try:
            c.execute("""
                INSERT INTO updated_plans (user_id, agent_type, original_plan, updated_plan, modification_summary)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, agent_type, original_plan, updated_plan, modification_summary))
            conn.commit()
            print(f"✅ Updated plan saved for user {user_id}, agent {agent_type}")
        except Exception as e:
            print(f"❌ Error saving updated plan: {str(e)}")
        finally:
            conn.close()

    def get_recent_chat_context(self, user_id, agent_type, limit=10):
        """Get recent chat messages for context (simplified format)"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        try:
            c.execute("""
                SELECT human_message, ai_response, created_at
                FROM chat_history
                WHERE user_id = ? AND agent_type = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (user_id, agent_type, limit))
            results = c.fetchall()

            if not results:
                return "No previous conversation history."

            context_lines = []
            for row in reversed(results):  # Show chronologically
                context_lines.append(f"User: {row['human_message']}")
                context_lines.append(f"Assistant: {row['ai_response'][:200]}...")  # Shortened for context
                context_lines.append("---")
            
            return "\n".join(context_lines)
        except Exception as e:
            print(f"❌ Error getting chat context: {str(e)}")
            return "Unable to load conversation history."
        finally:
            conn.close()

    def create_system_prompt(self, user_id, agent_type):
        """Create focused system prompt with memory"""
        user_context = self.get_user_context(user_id)
        current_plan_info = self.get_current_plan(user_id, agent_type)
        recent_chat = self.get_recent_chat_context(user_id, agent_type, limit=5)

        # Base user information
        user_info = f"""
USER PROFILE:
- Name: {user_context.get('name', 'Unknown')}
- Age: {user_context.get('age', 'Unknown')}
- Goals: {user_context.get('goals', 'Unknown')}
- Fitness Level: {user_context.get('fitness_level', 'Unknown')}
"""

        # Current plan status
        plan_status = "UPDATED" if current_plan_info['is_updated'] else "ORIGINAL"
        current_plan = f"""
CURRENT {plan_status} PLAN:
{current_plan_info['plan'][:1000]}{'...' if len(current_plan_info['plan']) > 1000 else ''}
"""

        # Recent conversation
        conversation_memory = f"""
RECENT CONVERSATION:
{recent_chat}
"""

        # Agent-specific prompts
        agent_roles = {
            "HealthSummary": """
You are a Health Data Analyst with COMPLETE MEMORY of our conversation.

ROLE: Analyze health status and provide summaries and insights.

MEMORY INSTRUCTIONS:
- Remember ALL our previous discussions about their health
- Reference past conversations naturally
- Track changes and progress over time
- When asked to update analysis, provide COMPLETE updated health summary

RESPONSE GUIDELINES:
- Keep regular responses under 300 words
- For health analysis updates, provide full detailed analysis
- Use encouraging and professional tone
- Remember previous recommendations and follow up on them
""",
            
            "FitnessTrainer": """
You are a Personal Trainer with COMPLETE MEMORY of our conversation and workout plans.

ROLE: Create and modify workout plans, track fitness progress.

MEMORY INSTRUCTIONS:
- Remember ALL our workout discussions and modifications
- Track their exercise preferences and limitations
- When they ask for "Plan B" or modifications, provide COMPLETE new workout plan
- Reference previous workouts and their feedback

RESPONSE GUIDELINES:
- Keep casual responses under 300 words
- For workout plan updates, provide FULL detailed plan with exercises, sets, reps
- Remember their available equipment and time constraints
- Build on previous workout discussions
""",
            
            "Nutritionist": """
You are a Professional Nutritionist with COMPLETE MEMORY of our conversation and meal plans.

ROLE: Create and modify meal plans, provide nutrition guidance.

MEMORY INSTRUCTIONS:
- Remember ALL our nutrition discussions and meal preferences
- Track dietary changes and preferences over time
- When asked for meal plan changes, provide COMPLETE updated meal plan
- Reference previous meal plans and their feedback

RESPONSE GUIDELINES:
- Keep casual responses under 300 words
- For meal plan updates, provide FULL detailed meal plans with recipes
- Remember their dietary restrictions and preferences
- Build on previous nutrition discussions
""",
            
            "HealthAdvisor": """
You are a Health & Wellness Advisor with COMPLETE MEMORY of our conversation.

ROLE: Provide lifestyle and wellness recommendations.

MEMORY INSTRUCTIONS:
- Remember ALL our wellness discussions and lifestyle recommendations
- Track their progress with sleep, stress, and lifestyle changes
- When asked for updated recommendations, provide COMPLETE wellness plan
- Reference previous advice and their experiences with it

RESPONSE GUIDELINES:
- Keep casual responses under 300 words
- For wellness plan updates, provide comprehensive updated recommendations
- Remember their lifestyle challenges and successes
- Build supportively on previous discussions
"""
        }

        base_prompt = agent_roles.get(agent_type, "You are a health advisor with complete conversation memory.")

        full_prompt = f"""{base_prompt}

{user_info}

{current_plan}

{conversation_memory}

CRITICAL MEMORY RULES:
1. You have COMPLETE memory of our entire conversation
2. Always reference relevant previous discussions
3. When updating plans, provide COMPLETE updated versions
4. Track progress and changes over time
5. Build naturally on our conversation history
6. Remember their specific preferences and feedback

"""
        return full_prompt

    def save_chat_message(self, user_id, agent_type, thread_id, human_message, ai_response):
        """Save chat message to database"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        try:
            c.execute("""
                INSERT INTO chat_history (user_id, agent_type, thread_id, human_message, ai_response)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, agent_type, thread_id, human_message, ai_response))
            conn.commit()
            print(f"✅ Chat message saved for user {user_id}, agent {agent_type}")
        except Exception as e:
            print(f"❌ Error saving chat message: {str(e)}")
        finally:
            conn.close()

    def get_chat_history(self, user_id, agent_type, limit=20):
        """Get formatted chat history for display"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        try:
            c.execute("""
                SELECT human_message, ai_response, created_at
                FROM chat_history
                WHERE user_id = ? AND agent_type = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (user_id, agent_type, limit))
            results = c.fetchall()

            history = []
            for row in reversed(results):  # Show chronologically
                history.append({
                    'human': row['human_message'],
                    'ai': row['ai_response'],
                    'timestamp': row['created_at']
                })
            print(f"✅ Chat history loaded: {len(history)} messages for user {user_id}, agent {agent_type}")
            return history
        except Exception as e:
            print(f"❌ Error getting chat history: {str(e)}")
            return []
        finally:
            conn.close()

    def clear_chat_history(self, user_id, agent_type):
        """Clear chat history and updated plans"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        try:
            # Clear chat history
            c.execute("""
                DELETE FROM chat_history
                WHERE user_id = ? AND agent_type = ?
            """, (user_id, agent_type))
            
            # Clear updated plans
            c.execute("""
                DELETE FROM updated_plans
                WHERE user_id = ? AND agent_type = ?
            """, (user_id, agent_type))
            
            conn.commit()
            print(f"✅ Chat history and updated plans cleared for user {user_id}, agent {agent_type}")
        except Exception as e:
            print(f"❌ Error clearing chat history: {str(e)}")
        finally:
            conn.close()

    def detect_plan_update(self, message, response):
        """Detect if the response contains a significant plan update"""
        update_keywords = [
            'updated plan', 'new plan', 'modified plan', 'changed plan',
            'here\'s the updated', 'here is the updated', 'revised plan',
            'alternative plan', 'plan b', 'plan c', 'different approach',
            'complete workout', 'full meal plan', 'updated analysis'
        ]
        
        message_lower = message.lower()
        response_lower = response.lower()
        
        # Check if user requested an update
        user_requested_update = any(keyword in message_lower for keyword in [
            'change', 'modify', 'update', 'different', 'alternative', 'new plan', 
            'plan b', 'revise', 'adjust'
        ])
        
        # Check if response contains updated content
        response_has_update = any(keyword in response_lower for keyword in update_keywords)
        
        # Must be substantial content (more than 500 characters)
        is_substantial = len(response) > 500
        
        return user_requested_update and response_has_update and is_substantial

    def generate_response(self, user_id, agent_type, message, thread_id):
        """Generate response with full conversation memory"""
        try:
            print(f"🔍 Generating response for user {user_id}, agent {agent_type}")
            
            # Validate input
            if not all([user_id, agent_type, message.strip()]):
                return {'success': False, 'error': 'Invalid input parameters'}

            valid_agents = ['HealthSummary', 'FitnessTrainer', 'Nutritionist', 'HealthAdvisor']
            if agent_type not in valid_agents:
                return {'success': False, 'error': 'Invalid agent type'}

            # Get system prompt with full memory
            system_prompt = self.create_system_prompt(user_id, agent_type)

            # Create final prompt
            final_prompt = f"""{system_prompt}

CURRENT USER MESSAGE: {message}

Remember: Use your complete conversation memory and provide helpful, personalized responses!
"""

            print(f"🔍 Sending prompt to LLM...")
            
            # Get response from LLM
            response = self.model.invoke(final_prompt)
            
            if not response or not response.content:
                return {'success': False, 'error': 'Empty response from LLM'}

            ai_response = response.content.strip()
            
            # Check for plan updates
            if self.detect_plan_update(message, ai_response):
                current_plan_info = self.get_current_plan(user_id, agent_type)
                modification_summary = f"User requested: {message[:200]}..."
                
                self.save_updated_plan(
                    user_id, agent_type, 
                    current_plan_info['plan'], 
                    ai_response, 
                    modification_summary
                )
                print(f"🔄 Plan update detected and saved")
            
            # Save chat message
            self.save_chat_message(user_id, agent_type, thread_id, message, ai_response)
            
            print(f"✅ Response generated successfully")
            return {'success': True, 'response': ai_response}

        except Exception as e:
            error_msg = f"Error generating response: {str(e)}"
            print(f"❌ ChatManager Error: {error_msg}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': error_msg}


# Create global instance
chat_manager = ChatManager()