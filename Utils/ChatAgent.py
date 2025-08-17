# Utils/ChatAgent.py
# Enhanced ChatAgent with LangChain Memory Integration

import os
import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from Utils.MemoryManager import memory_manager

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', 'apikey.env'))


class EnhancedChatManager:
    """Enhanced Chat Manager with LangChain Memory and Context Awareness"""
    
    def __init__(self):
        self.db_path = 'healthagent.db'
        
        # Initialize LLM
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
            print("✅ Enhanced ChatManager LLM initialized successfully")
        except Exception as e:
            print(f"❌ Error initializing Enhanced ChatManager LLM: {str(e)}")
            raise

    def get_user_profile_context(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive user profile for context"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        try:
            # Get user and profile data
            c.execute("""
                SELECT u.first_name, u.age as user_age, p.*
                FROM users u
                LEFT JOIN profiles p ON u.id = p.user_id
                WHERE u.id = ?
            """, (user_id,))
            data = c.fetchone()
            
            if not data:
                return {'name': 'Unknown User', 'profile_complete': False}

            # Build comprehensive context
            profile = {
                'name': data['first_name'],
                'profile_complete': bool(data['height']),  # Check if profile exists
                'age': data['age'] or data['user_age'],
                'physical_stats': {
                    'height': data['height'],
                    'weight': data['weight'], 
                    'bmi': data['bmi']
                } if data['height'] else {},
                'goals': {
                    'primary': data['primary_goal'],
                    'specific': data['specific_goals']
                } if data['primary_goal'] else {},
                'fitness': {
                    'level': data['fitness_level'],
                    'activity_level': data['activity_level'],
                    'preference': data['workout_preference'],
                    'days_per_week': data['workout_days'],
                    'duration': data['workout_duration'],
                    'equipment': json.loads(data['available_equipment']) if data['available_equipment'] else []
                } if data['fitness_level'] else {},
                'health': {
                    'previous_injuries': data['previous_injuries'],
                    'current_injuries': data['current_injuries'],
                    'chronic_conditions': data['chronic_conditions'],
                    'medications': data['medications_supplements']
                },
                'nutrition': {
                    'preferences': data['dietary_preferences'],
                    'allergies': data['allergies'],
                    'restrictions': data['food_restrictions'],
                    'meals_per_day': data['meals_per_day'],
                    'cooking_skill': data['cooking_skill'],
                    'budget': data['budget']
                } if data['dietary_preferences'] else {},
                'lifestyle': {
                    'sleep_hours': data['sleep_hours'],
                    'sleep_quality': data['sleep_quality'],
                    'stress_level': self.map_stress_level(data['stress_level']),
                    'water_intake': data['water_intake'],
                    'smoking': data['smoking_status'],
                    'alcohol': data['alcohol_consumption']
                } if data['sleep_hours'] else {}
            }

            print(f"✅ Profile context loaded for user {user_id}")
            return profile

        except Exception as e:
            print(f"❌ Error getting user profile: {str(e)}")
            return {'name': 'User', 'profile_complete': False}
        finally:
            conn.close()

    def map_stress_level(self, level):
        """Convert stress level to descriptive text"""
        if isinstance(level, str) or level is None:
            return level or 'unknown'
        return {
            1: 'very low', 2: 'low', 3: 'mild', 4: 'moderate', 5: 'moderate',
            6: 'moderate', 7: 'high', 8: 'high', 9: 'very high', 10: 'extreme'
        }.get(level, 'moderate')

    def get_current_plan_context(self, user_id: int, agent_type: str) -> Dict[str, Any]:
        """Get current plan with version history"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            # First check for updated plans
            c.execute("""
                SELECT up.updated_plan, up.modification_summary, up.version_number, up.created_at
                FROM updated_plans up
                WHERE up.user_id = ? AND up.agent_type = ? AND up.is_current = TRUE
                ORDER BY up.created_at DESC LIMIT 1
            """, (user_id, agent_type))
            
            updated_result = c.fetchone()
            
            if updated_result:
                return {
                    'current_plan': updated_result[0],
                    'is_updated': True,
                    'last_modification': updated_result[1],
                    'version': updated_result[2],
                    'last_updated': updated_result[3]
                }
            
            # Get original plan
            c.execute("""
                SELECT recommendation, created_at FROM agent_history
                WHERE user_id = ? AND agent_type = ?
                ORDER BY created_at DESC LIMIT 1
            """, (user_id, agent_type))
            
            original_result = c.fetchone()
            
            if original_result:
                return {
                    'current_plan': original_result[0],
                    'is_updated': False,
                    'last_modification': None,
                    'version': 1,
                    'created': original_result[1]
                }
            
            return {
                'current_plan': None,
                'is_updated': False,
                'message': 'No previous plan found. Ready to create your first personalized plan!'
            }
            
        except Exception as e:
            print(f"❌ Error getting current plan: {str(e)}")
            return {'current_plan': None, 'error': str(e)}
        finally:
            conn.close()

    def create_enhanced_system_prompt(self, user_id: int, agent_type: str) -> str:
        """Create comprehensive system prompt with full context"""
        
        # Get all context data
        user_profile = self.get_user_profile_context(user_id)
        plan_context = self.get_current_plan_context(user_id, agent_type)
        conversation_context = memory_manager.get_conversation_context(user_id, agent_type)
        
        # Base agent personalities
        agent_personalities = {
            "HealthSummary": {
                "role": "Professional Health Data Analyst",
                "personality": "analytical, encouraging, data-focused",
                "expertise": "health metrics analysis, progress tracking, trend identification",
                "response_style": "structured, evidence-based, motivational"
            },
            "FitnessTrainer": {
                "role": "Expert Personal Trainer & Exercise Physiologist", 
                "personality": "motivating, knowledgeable, safety-conscious",
                "expertise": "workout design, exercise form, progression planning, injury prevention",
                "response_style": "practical, detailed, encouraging with specific instructions"
            },
            "Nutritionist": {
                "role": "Certified Nutritionist & Meal Planning Specialist",
                "personality": "caring, practical, science-based", 
                "expertise": "meal planning, nutrition science, dietary modifications, food safety",
                "response_style": "informative, practical, with easy-to-follow recommendations"
            },
            "HealthAdvisor": {
                "role": "Holistic Health & Wellness Coach",
                "personality": "compassionate, wise, holistic-thinking",
                "expertise": "lifestyle optimization, stress management, sleep improvement, habit formation", 
                "response_style": "supportive, comprehensive, with actionable lifestyle advice"
            }
        }

        agent_info = agent_personalities.get(agent_type, agent_personalities["HealthAdvisor"])

        # Format conversation history for context
        recent_messages_text = ""
        if conversation_context['recent_messages']:
            recent_messages_text = "\n".join([
                f"{msg['role'].title()}: {msg['content'][:150]}..."
                for msg in conversation_context['recent_messages'][-6:]  # Last 3 exchanges
            ])

        # Format user profile information
        profile_text = f"User: {user_profile['name']}"
        if user_profile['profile_complete']:
            if user_profile.get('physical_stats'):
                profile_text += f" | Age: {user_profile['age']} | BMI: {user_profile['physical_stats'].get('bmi', 'unknown')}"
            if user_profile.get('goals', {}).get('primary'):
                profile_text += f" | Goal: {user_profile['goals']['primary']}"

        # Current plan status
        plan_status_text = ""
        if plan_context['current_plan']:
            status = "UPDATED" if plan_context['is_updated'] else "ORIGINAL"
            plan_status_text = f"CURRENT {status} PLAN: {plan_context['current_plan'][:500]}..."
            if plan_context.get('last_modification'):
                plan_status_text += f"\n📝 Last Change: {plan_context['last_modification']}"

        # Conversation summary for long chats
        summary_text = ""
        if conversation_context.get('summary'):
            summary_text = f"CONVERSATION SUMMARY: {conversation_context['summary']}"

        # Create the comprehensive system prompt
        system_prompt = f"""You are {agent_info['role']} with COMPLETE CONVERSATION MEMORY and full access to user context.

🎯 ROLE & PERSONALITY:
- Role: {agent_info['role']}
- Personality: {agent_info['personality']} 
- Expertise: {agent_info['expertise']}
- Response Style: {agent_info['response_style']}

👤 USER CONTEXT:
{profile_text}

📋 {plan_status_text}

💭 CONVERSATION MEMORY:
Total Messages: {conversation_context.get('message_count', 0)}
{summary_text}

Recent Discussion:
{recent_messages_text}

🧠 MEMORY & CONTEXT RULES:
1. ✅ COMPLETE MEMORY: You remember our ENTIRE conversation history
2. 🔄 CONTEXT AWARENESS: Always reference relevant previous discussions
3. 📈 PROGRESS TRACKING: Track changes, feedback, and user progress over time
4. 🎯 PERSONALIZATION: Adapt responses based on user's profile and history
5. 🔗 CONTINUITY: Build naturally on our conversation flow

📝 RESPONSE GUIDELINES:
- Keep casual responses under 300 words
- For plan updates/modifications, provide COMPLETE detailed plans
- Always acknowledge and build on previous discussions
- Reference user's specific preferences, constraints, and feedback
- Use encouraging, professional tone appropriate for your role
- When user asks for changes, provide FULL updated plans, not just modifications

🚨 CRITICAL: 
- You have PERFECT memory of our conversation
- When updating plans, provide COMPLETE new versions
- Always reference relevant past discussions naturally
- Remember user's specific goals, constraints, and preferences

Current user message will follow. Respond with your full expertise and memory!"""

        return system_prompt

    def detect_plan_update_advanced(self, user_message: str, ai_response: str, conversation_context: Dict) -> bool:
        """Advanced plan update detection with context awareness"""
        
        # Keywords that suggest plan modification requests
        update_request_keywords = [
            'change', 'modify', 'update', 'different', 'alternative', 'new plan',
            'plan b', 'plan c', 'revise', 'adjust', 'replace', 'switch',
            'تغییر', 'تبدیل', 'جدید', 'متفاوت', 'دیگه', 'عوض'
        ]
        
        # Keywords that indicate the response contains a plan
        plan_response_keywords = [
            'updated plan', 'new plan', 'modified plan', 'here\'s your plan',
            'complete plan', 'revised plan', 'alternative plan', 'full plan',
            'workout plan', 'meal plan', 'nutrition plan', 'fitness plan'
        ]
        
        # Check user intent
        user_msg_lower = user_message.lower()
        user_wants_update = any(keyword in user_msg_lower for keyword in update_request_keywords)
        
        # Check AI response content
        ai_response_lower = ai_response.lower()
        response_contains_plan = any(keyword in ai_response_lower for keyword in plan_response_keywords)
        
        # Check response length (substantial content)
        is_substantial = len(ai_response) > 800
        
        # Check if response has structured format (likely a plan)
        has_structure = any(marker in ai_response for marker in ['##', '**', '1.', '2.', 'Week', 'Day'])
        
        # Additional context check - if recent conversation was about modifying plans
        recent_context_about_plans = False
        if conversation_context.get('recent_messages'):
            recent_text = ' '.join([msg['content'] for msg in conversation_context['recent_messages'][-4:]])
            recent_context_about_plans = any(keyword in recent_text.lower() for keyword in update_request_keywords)
        
        # Final decision logic
        is_plan_update = (
            user_wants_update and 
            response_contains_plan and 
            is_substantial and
            has_structure
        ) or (
            recent_context_about_plans and 
            response_contains_plan and 
            is_substantial
        )
        
        print(f"🔍 Plan Update Detection: user_wants={user_wants_update}, response_has_plan={response_contains_plan}, substantial={is_substantial}, structured={has_structure} → Result: {is_plan_update}")
        
        return is_plan_update

    def save_updated_plan_with_versioning(self, user_id: int, agent_type: str, updated_plan: str, 
                                        modification_summary: str, conversation_id: int) -> bool:
        """Save updated plan with proper versioning"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            # Mark current plans as not current
            c.execute("""
                UPDATE updated_plans 
                SET is_current = FALSE 
                WHERE user_id = ? AND agent_type = ?
            """, (user_id, agent_type))
            
            # Get next version number
            c.execute("""
                SELECT COALESCE(MAX(version_number), 0) + 1 
                FROM updated_plans 
                WHERE user_id = ? AND agent_type = ?
            """, (user_id, agent_type))
            next_version = c.fetchone()[0]
            
            # Get original plan ID
            c.execute("""
                SELECT id FROM agent_history
                WHERE user_id = ? AND agent_type = ?
                ORDER BY created_at DESC LIMIT 1
            """, (user_id, agent_type))
            original_result = c.fetchone()
            original_plan_id = original_result[0] if original_result else None
            
            # Insert new updated plan
            c.execute("""
                INSERT INTO updated_plans
                (user_id, agent_type, original_plan_id, updated_plan, modification_summary, 
                 conversation_id, version_number, is_current)
                VALUES (?, ?, ?, ?, ?, ?, ?, TRUE)
            """, (user_id, agent_type, original_plan_id, updated_plan, modification_summary, 
                  conversation_id, next_version))
            
            conn.commit()
            print(f"✅ Saved updated plan v{next_version} for user {user_id}, agent {agent_type}")
            return True
            
        except Exception as e:
            print(f"❌ Error saving updated plan: {str(e)}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def generate_response(self, user_id: int, agent_type: str, message: str, thread_id: str) -> Dict[str, Any]:
        """Generate enhanced response with full memory and context"""
        try:
            print(f"🔍 Generating enhanced response for user {user_id}, agent {agent_type}")
            
            # Validate inputs
            if not all([user_id, agent_type, message.strip()]):
                return {'success': False, 'error': 'Invalid input parameters'}

            valid_agents = ['HealthSummary', 'FitnessTrainer', 'Nutritionist', 'HealthAdvisor']
            if agent_type not in valid_agents:
                return {'success': False, 'error': f'Invalid agent type. Must be one of: {valid_agents}'}

            # Get comprehensive context
            conversation_context = memory_manager.get_conversation_context(user_id, agent_type)
            system_prompt = self.create_enhanced_system_prompt(user_id, agent_type)
            
            # Create messages for LLM
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"User message: {message}")
            ]
            
            print(f"🔍 Sending enhanced prompt to LLM...")
            
            # Generate response
            response = self.model.invoke(messages)
            
            if not response or not response.content:
                return {'success': False, 'error': 'Empty response from LLM'}

            ai_response = response.content.strip()
            
            # Advanced plan update detection
            contains_plan_update = self.detect_plan_update_advanced(message, ai_response, conversation_context)
            
            # Save conversation to memory system
            memory_success = memory_manager.add_message(
                user_id, agent_type, message, ai_response, contains_plan_update
            )
            
            if not memory_success:
                print("⚠️ Warning: Failed to save to memory system")
            
            # Handle plan updates with versioning
            if contains_plan_update:
                # Get the conversation ID for the AI response
                session_id = memory_manager.get_session_id(user_id, agent_type)
                conn = sqlite3.connect(self.db_path)
                c = conn.cursor()
                c.execute("""
                    SELECT id FROM conversations 
                    WHERE session_id = ? AND message_type = 'assistant'
                    ORDER BY message_order DESC LIMIT 1
                """, (session_id,))
                result = c.fetchone()
                conversation_id = result[0] if result else None
                conn.close()
                
                if conversation_id:
                    modification_summary = f"User requested: {message[:200]}..."
                    self.save_updated_plan_with_versioning(
                        user_id, agent_type, ai_response, modification_summary, conversation_id
                    )
                    print(f"🔄 Plan update saved with versioning")
            
            print(f"✅ Enhanced response generated successfully (plan_update: {contains_plan_update})")
            return {
                'success': True, 
                'response': ai_response,
                'contains_plan_update': contains_plan_update,
                'conversation_context': {
                    'message_count': conversation_context.get('message_count', 0),
                    'session_id': conversation_context.get('session_id')
                }
            }

        except Exception as e:
            error_msg = f"Enhanced ChatManager Error: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': error_msg}

    def get_conversation_history(self, user_id: int, agent_type: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get formatted conversation history"""
        try:
            context = memory_manager.get_conversation_context(user_id, agent_type)
            
            # Get more detailed history from database
            session_id = context['session_id']
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            c.execute("""
                SELECT message_type, content, timestamp, contains_plan_update
                FROM conversations
                WHERE session_id = ?
                ORDER BY message_order DESC
                LIMIT ?
            """, (session_id, limit * 2))  # *2 for human + AI pairs
            
            messages = []
            current_pair = {}
            
            for row in reversed(c.fetchall()):  # Reverse to chronological
                if row['message_type'] == 'human':
                    current_pair = {
                        'human': row['content'],
                        'timestamp': row['timestamp']
                    }
                elif row['message_type'] == 'assistant' and current_pair:
                    current_pair['ai'] = row['content']
                    current_pair['isUpdate'] = bool(row['contains_plan_update'])
                    messages.append(current_pair)
                    current_pair = {}
            
            conn.close()
            print(f"✅ Retrieved {len(messages)} conversation pairs")
            return messages
            
        except Exception as e:
            print(f"❌ Error getting conversation history: {str(e)}")
            return []

    def clear_conversation(self, user_id: int, agent_type: str) -> bool:
        """Clear conversation and reset to original plan"""
        try:
            # Clear memory system
            success = memory_manager.clear_session(user_id, agent_type)
            
            if success:
                # Also reset plans to original
                conn = sqlite3.connect(self.db_path)
                c = conn.cursor()
                c.execute("""
                    UPDATE updated_plans 
                    SET is_current = FALSE 
                    WHERE user_id = ? AND agent_type = ?
                """, (user_id, agent_type))
                conn.commit()
                conn.close()
                
                print(f"✅ Cleared conversation and reset plans for user {user_id}, agent {agent_type}")
            
            return success
            
        except Exception as e:
            print(f"❌ Error clearing conversation: {str(e)}")
            return False

    def get_session_analytics(self, user_id: int, agent_type: str) -> Dict[str, Any]:
        """Get session analytics and insights"""
        return memory_manager.get_session_analytics(user_id, agent_type)


# Create global enhanced chat manager instance  
enhanced_chat_manager = EnhancedChatManager()