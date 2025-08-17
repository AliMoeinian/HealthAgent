# Utils/MemoryManager.py
# Enhanced Memory Management with LangChain

import os
import json
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dotenv import load_dotenv

# Updated LangChain imports - fixed deprecated imports
from langchain.memory import ConversationBufferWindowMemory, ConversationSummaryMemory
from langchain_community.chat_message_histories import SQLChatMessageHistory  # Updated import
from langchain.schema import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', 'apikey.env'))


class HealthAgentMemoryManager:
    """Advanced memory management for Health Agent with LangChain integration"""
    
    def __init__(self, db_path='healthagent.db'):
        self.db_path = db_path
        
        # Initialize LLM for summaries
        try:
            self.llm = ChatOpenAI(
                temperature=0.3,  # Lower temperature for consistent summaries
                model="google/gemma-3-12b-it:free",
                base_url="https://openrouter.ai/api/v1",
                api_key=os.getenv("OPENROUTER_API_KEY"),
                max_retries=3,
                timeout=120
            )
            print("✅ MemoryManager LLM initialized successfully")
        except Exception as e:
            print(f"❌ Error initializing MemoryManager LLM: {str(e)}")
            raise

    def get_session_id(self, user_id: int, agent_type: str) -> str:
        """Get or create session ID for user-agent combination"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            # Check for active session
            c.execute("""
                SELECT session_id FROM conversation_sessions
                WHERE user_id = ? AND agent_type = ? AND status = 'active'
                ORDER BY last_activity DESC LIMIT 1
            """, (user_id, agent_type))
            
            result = c.fetchone()
            if result:
                session_id = result[0]
                # Update last activity
                c.execute("""
                    UPDATE conversation_sessions 
                    SET last_activity = CURRENT_TIMESTAMP
                    WHERE session_id = ?
                """, (session_id,))
                conn.commit()
                return session_id
            
            # Create new session
            session_id = f"{agent_type}_{user_id}_{int(datetime.now().timestamp())}"
            c.execute("""
                INSERT INTO conversation_sessions
                (user_id, agent_type, session_id, session_name)
                VALUES (?, ?, ?, ?)
            """, (user_id, agent_type, session_id, f"{agent_type} Chat Session"))
            
            conn.commit()
            print(f"✅ Created new session: {session_id}")
            return session_id
            
        except Exception as e:
            print(f"❌ Error managing session: {str(e)}")
            return f"fallback_{agent_type}_{user_id}"
        finally:
            conn.close()

    def get_buffer_window_memory(self, user_id: int, agent_type: str, window_size: int = 10) -> ConversationBufferWindowMemory:
        """Get conversation buffer window memory (recent N messages)"""
        session_id = self.get_session_id(user_id, agent_type)
        
        # Create custom SQLite-based message history
        message_history = self._get_recent_messages(session_id, window_size)
        
        memory = ConversationBufferWindowMemory(
            k=window_size,
            return_messages=True,
            memory_key="chat_history"
        )
        
        # Load recent messages into memory
        for msg in message_history:
            if msg['type'] == 'human':
                memory.chat_memory.add_user_message(msg['content'])
            else:
                memory.chat_memory.add_ai_message(msg['content'])
        
        return memory

    def get_summary_memory(self, user_id: int, agent_type: str) -> ConversationSummaryMemory:
        """Get conversation summary memory (for long conversations)"""
        session_id = self.get_session_id(user_id, agent_type)
        
        # Get or create summary
        summary = self._get_or_create_session_summary(session_id, user_id, agent_type)
        
        memory = ConversationSummaryMemory(
            llm=self.llm,
            return_messages=True,
            memory_key="chat_history"
        )
        
        # Set existing summary if available
        if summary:
            memory.buffer = summary
        
        return memory

    def _get_recent_messages(self, session_id: str, limit: int = 10) -> List[Dict]:
        """Get recent messages from database"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        try:
            c.execute("""
                SELECT message_type, content, timestamp
                FROM conversations
                WHERE session_id = ?
                ORDER BY message_order DESC
                LIMIT ?
            """, (session_id, limit * 2))  # *2 because we have both human and AI messages
            
            messages = []
            for row in reversed(c.fetchall()):  # Reverse to chronological order
                messages.append({
                    'type': row['message_type'],
                    'content': row['content'],
                    'timestamp': row['timestamp']
                })
            
            return messages
            
        except Exception as e:
            print(f"❌ Error getting recent messages: {str(e)}")
            return []
        finally:
            conn.close()

    def _get_or_create_session_summary(self, session_id: str, user_id: int, agent_type: str) -> Optional[str]:
        """Get existing summary or create new one for long conversations"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            # Check if we have a recent summary
            c.execute("""
                SELECT summary_content FROM memory_summaries
                WHERE session_id = ? AND summary_type = 'session_summary' AND is_active = TRUE
                ORDER BY created_at DESC LIMIT 1
            """, (session_id,))
            
            result = c.fetchone()
            if result:
                return result[0]
            
            # Get message count to decide if we need summary
            c.execute("""
                SELECT COUNT(*) FROM conversations WHERE session_id = ?
            """, (session_id,))
            
            message_count = c.fetchone()[0]
            
            # Create summary if conversation is long enough (>20 messages)
            if message_count > 20:
                return self._create_conversation_summary(session_id, user_id, agent_type)
            
            return None
            
        except Exception as e:
            print(f"❌ Error getting session summary: {str(e)}")
            return None
        finally:
            conn.close()

    def _create_conversation_summary(self, session_id: str, user_id: int, agent_type: str) -> str:
        """Create a summary of the conversation using LLM"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            # Get conversation history
            c.execute("""
                SELECT message_type, content FROM conversations
                WHERE session_id = ?
                ORDER BY message_order
            """, (session_id,))
            
            messages = c.fetchall()
            if not messages:
                return ""
            
            # Format conversation for summarization
            conversation_text = ""
            for msg_type, content in messages[:-10]:  # Exclude recent 10 messages
                role = "User" if msg_type == "human" else "Assistant"
                conversation_text += f"{role}: {content[:200]}...\n"
            
            # Create summary prompt
            summary_prompt = f"""
Please create a concise summary of this conversation between a user and their {agent_type}:

{conversation_text}

Focus on:
- Key topics discussed
- Important decisions made
- User's preferences and feedback
- Plan modifications or updates
- Health goals and progress

Summary:
"""
            
            # Generate summary
            response = self.llm.invoke(summary_prompt)
            summary = response.content.strip()
            
            # Save summary to database
            c.execute("""
                INSERT INTO memory_summaries
                (session_id, user_id, agent_type, summary_type, summary_content)
                VALUES (?, ?, ?, 'session_summary', ?)
            """, (session_id, user_id, agent_type, summary))
            
            conn.commit()
            print(f"✅ Created conversation summary for session {session_id}")
            return summary
            
        except Exception as e:
            print(f"❌ Error creating conversation summary: {str(e)}")
            return ""
        finally:
            conn.close()

    def add_message(self, user_id: int, agent_type: str, human_message: str, ai_response: str, 
                   contains_plan_update: bool = False) -> bool:
        """Add new message pair to conversation with context tracking"""
        session_id = self.get_session_id(user_id, agent_type)
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            # Get next message order
            c.execute("""
                SELECT COALESCE(MAX(message_order), 0) + 1 
                FROM conversations WHERE session_id = ?
            """, (session_id,))
            next_order = c.fetchone()[0]
            
            # Add human message
            c.execute("""
                INSERT INTO conversations
                (session_id, user_id, agent_type, message_type, content, message_order, contains_plan_update)
                VALUES (?, ?, ?, 'human', ?, ?, ?)
            """, (session_id, user_id, agent_type, human_message, next_order, False))
            
            human_conversation_id = c.lastrowid
            
            # Add AI response
            c.execute("""
                INSERT INTO conversations
                (session_id, user_id, agent_type, message_type, content, message_order, contains_plan_update)
                VALUES (?, ?, ?, 'assistant', ?, ?, ?)
            """, (session_id, user_id, agent_type, ai_response, next_order + 1, contains_plan_update))
            
            ai_conversation_id = c.lastrowid
            
            # Update session stats
            c.execute("""
                UPDATE conversation_sessions
                SET message_count = message_count + 2,
                    last_activity = CURRENT_TIMESTAMP
                WHERE session_id = ?
            """, (session_id,))
            
            # Detect and save context references
            self._extract_context_references(human_conversation_id, human_message, user_id, agent_type)
            
            conn.commit()
            print(f"✅ Added message pair to session {session_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error adding message: {str(e)}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def _extract_context_references(self, conversation_id: int, message: str, user_id: int, agent_type: str):
        """Extract and save context references from user message"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            message_lower = message.lower()
            
            # Plan references
            plan_keywords = ['plan', 'برنامه', 'program', 'routine', 'schedule']
            temporal_keywords = ['last', 'previous', 'قبلی', 'اخیر', 'current', 'فعلی']
            
            if any(keyword in message_lower for keyword in plan_keywords):
                # Get the most recent plan
                c.execute("""
                    SELECT id FROM agent_history
                    WHERE user_id = ? AND agent_type = ?
                    ORDER BY created_at DESC LIMIT 1
                """, (user_id, agent_type))
                
                result = c.fetchone()
                if result:
                    plan_id = result[0]
                    c.execute("""
                        INSERT INTO context_references
                        (conversation_id, reference_type, reference_id, reference_text, confidence_score)
                        VALUES (?, 'plan', ?, ?, ?)
                    """, (conversation_id, plan_id, message[:200], 0.8))
            
            # Previous message references
            reference_keywords = ['that', 'this', 'it', 'اون', 'این', 'همون']
            if any(keyword in message_lower for keyword in reference_keywords):
                c.execute("""
                    INSERT INTO context_references
                    (conversation_id, reference_type, reference_text, confidence_score)
                    VALUES (?, 'previous_message', ?, ?)
                """, (conversation_id, message[:200], 0.6))
            
            conn.commit()
            
        except Exception as e:
            print(f"❌ Error extracting context references: {str(e)}")
        finally:
            conn.close()

    def get_conversation_context(self, user_id: int, agent_type: str, include_summary: bool = True) -> Dict[str, Any]:
        """Get comprehensive conversation context for prompt injection"""
        session_id = self.get_session_id(user_id, agent_type)
        
        context = {
            'session_id': session_id,
            'recent_messages': [],
            'summary': '',
            'references': [],
            'message_count': 0
        }
        
        # Get recent messages (BufferWindow)
        buffer_memory = self.get_buffer_window_memory(user_id, agent_type, window_size=10)
        context['recent_messages'] = self._format_memory_messages(buffer_memory.chat_memory.messages)
        
        # Get summary for long conversations
        if include_summary:
            summary_memory = self.get_summary_memory(user_id, agent_type)
            context['summary'] = summary_memory.buffer or ''
        
        # Get context references
        context['references'] = self._get_recent_references(session_id)
        
        # Get total message count
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        try:
            c.execute("SELECT message_count FROM conversation_sessions WHERE session_id = ?", (session_id,))
            result = c.fetchone()
            context['message_count'] = result[0] if result else 0
        except:
            context['message_count'] = 0
        finally:
            conn.close()
        
        return context

    def _format_memory_messages(self, messages: List[BaseMessage]) -> List[Dict]:
        """Format LangChain messages for context"""
        formatted = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                formatted.append({'role': 'user', 'content': msg.content})
            elif isinstance(msg, AIMessage):
                formatted.append({'role': 'assistant', 'content': msg.content})
        return formatted

    def _get_recent_references(self, session_id: str, limit: int = 5) -> List[Dict]:
        """Get recent context references"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        try:
            c.execute("""
                SELECT cr.reference_type, cr.reference_id, cr.reference_text, cr.confidence_score
                FROM context_references cr
                JOIN conversations c ON cr.conversation_id = c.id
                WHERE c.session_id = ?
                ORDER BY cr.created_at DESC
                LIMIT ?
            """, (session_id, limit))
            
            return [dict(row) for row in c.fetchall()]
            
        except Exception as e:
            print(f"❌ Error getting references: {str(e)}")
            return []
        finally:
            conn.close()

    def clear_session(self, user_id: int, agent_type: str) -> bool:
        """Clear conversation session and related data"""
        session_id = self.get_session_id(user_id, agent_type)
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            # Mark session as inactive
            c.execute("""
                UPDATE conversation_sessions
                SET status = 'cleared'
                WHERE session_id = ?
            """, (session_id,))
            
            # Clear related data (optional - you might want to keep for analytics)
            c.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))
            c.execute("DELETE FROM memory_summaries WHERE session_id = ?", (session_id,))
            
            conn.commit()
            print(f"✅ Cleared session {session_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error clearing session: {str(e)}")
            return False
        finally:
            conn.close()

    def get_session_analytics(self, user_id: int, agent_type: str) -> Dict[str, Any]:
        """Get conversation analytics for insights"""
        session_id = self.get_session_id(user_id, agent_type)
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        analytics = {
            'total_messages': 0,
            'plan_updates_count': 0,
            'session_duration_minutes': 0,
            'most_recent_activity': None,
            'topics_discussed': []
        }
        
        try:
            # Basic stats
            c.execute("""
                SELECT 
                    COUNT(*) as total_messages,
                    SUM(CASE WHEN contains_plan_update = 1 THEN 1 ELSE 0 END) as plan_updates,
                    MIN(timestamp) as first_message,
                    MAX(timestamp) as last_message
                FROM conversations
                WHERE session_id = ?
            """, (session_id,))
            
            result = c.fetchone()
            if result:
                analytics['total_messages'] = result[0]
                analytics['plan_updates_count'] = result[1]
                
                if result[2] and result[3]:
                    first = datetime.fromisoformat(result[2].replace('Z', '+00:00'))
                    last = datetime.fromisoformat(result[3].replace('Z', '+00:00'))
                    analytics['session_duration_minutes'] = (last - first).total_seconds() / 60
                    analytics['most_recent_activity'] = result[3]
            
            return analytics
            
        except Exception as e:
            print(f"❌ Error getting analytics: {str(e)}")
            return analytics
        finally:
            conn.close()


# Create global memory manager instance
memory_manager = HealthAgentMemoryManager()