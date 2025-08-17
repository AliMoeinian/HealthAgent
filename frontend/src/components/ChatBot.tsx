import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface ChatMessage {
  human: string;
  ai: string;
  timestamp: string;
  isUpdate?: boolean; // Flag for plan updates
}

interface ChatBotProps {
  userId: number;
  agentType: 'HealthSummary' | 'FitnessTrainer' | 'Nutritionist' | 'HealthAdvisor';
  agentTitle: string;
  isVisible: boolean;
  onClose: () => void;
}

const ChatBot: React.FC<ChatBotProps> = ({ userId, agentType, agentTitle, isVisible, onClose }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [currentMessage, setCurrentMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const [threadId, setThreadId] = useState<string>('');
  const [error, setError] = useState<string>('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (isVisible && userId && agentType) {
      loadChatHistory();
      setThreadId(`${agentType}_${userId}_${Date.now()}`);
      setError('');
    }
  }, [isVisible, userId, agentType]);

  const detectPlanUpdate = (message: string, response: string): boolean => {
    const updateKeywords = [
      'updated plan', 'new plan', 'modified plan', 'revised plan',
      'here\'s the updated', 'here is the updated', 'alternative plan',
      'plan b', 'plan c', 'different approach', 'changed plan'
    ];
    
    const userRequestsUpdate = message.toLowerCase().includes('change') || 
                              message.toLowerCase().includes('modify') || 
                              message.toLowerCase().includes('update') ||
                              message.toLowerCase().includes('different');
    
    const responseHasUpdate = updateKeywords.some(keyword => 
      response.toLowerCase().includes(keyword)
    );
    
    return userRequestsUpdate && responseHasUpdate && response.length > 500;
  };

  const loadChatHistory = async () => {
    setIsLoadingHistory(true);
    setError('');
    try {
      const response = await axios.post('http://localhost:5000/api/chat-history', {
        userId,
        agentType,
        limit: 20,
      });
      
      const history = response.data.history || [];
      const processedHistory = history.map((msg: ChatMessage) => ({
        ...msg,
        isUpdate: detectPlanUpdate(msg.human, msg.ai)
      }));
      
      setMessages(processedHistory);
    } catch (error: any) {
      setError('Failed to load chat history');
    } finally {
      setIsLoadingHistory(false);
    }
  };

  const sendMessage = async () => {
    if (!currentMessage.trim() || isLoading) return;

    const userMessage = currentMessage.trim();
    setCurrentMessage('');
    setIsLoading(true);
    setError('');

    try {
      const response = await axios.post('http://localhost:5000/api/chat', {
        userId,
        agentType,
        message: userMessage,
        threadId,
      });

      if (response.data.success) {
        const aiResponse = response.data.response;
        const isUpdate = detectPlanUpdate(userMessage, aiResponse);
        
        const newMessage: ChatMessage = {
          human: userMessage,
          ai: aiResponse,
          timestamp: new Date().toISOString(),
          isUpdate: isUpdate
        };
        
        setMessages((prev) => [...prev, newMessage]);
        
        // Show update notification if this was a plan update
        if (isUpdate) {
          setTimeout(() => {
            alert('🎉 Your plan has been updated! The changes will be reflected in the main dashboard.');
          }, 1000);
        }
      } else {
        setError(response.data.error || 'Failed to send message');
      }
    } catch (error: any) {
      setError(error.response?.data.error || 'An unexpected error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const clearChat = async () => {
    if (window.confirm('Are you sure you want to clear the chat history? This will also reset your plan to the original version.')) {
      try {
        await axios.post('http://localhost:5000/api/clear-chat', {
          userId,
          agentType,
        });
        setMessages([]);
        setError('');
      } catch (error: any) {
        setError('Failed to clear chat history');
      }
    }
  };

  const getAgentEmoji = (type: string) => {
    const emojis = {
      HealthSummary: '📊',
      FitnessTrainer: '🏋️',
      Nutritionist: '🥗',
      HealthAdvisor: '❤️',
    };
    return emojis[type as keyof typeof emojis] || '🤖';
  };

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getSampleQuestions = () => {
    const samples = {
      HealthSummary: [
        "What's my current health status?",
        "How can I improve my BMI?",
        "What are my key strengths?",
      ],
      FitnessTrainer: [
        "Change my workout to focus more on cardio",
        "I want a different Plan B for arms",
        "Can you modify my rest days?",
      ],
      Nutritionist: [
        "Create a vegetarian version of my meal plan",
        "I want more protein in my diet",
        "Can you suggest breakfast alternatives?",
      ],
      HealthAdvisor: [
        "How can I improve my sleep quality?",
        "Give me stress management techniques",
        "Update my wellness routine",
      ]
    };
    return samples[agentType] || [];
  };

  if (!isVisible) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-2xl w-full max-w-2xl h-[80vh] flex flex-col">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white p-4 rounded-t-lg flex justify-between items-center">
          <div className="flex items-center space-x-3">
            <span className="text-2xl">{getAgentEmoji(agentType)}</span>
            <div>
              <h3 className="text-lg font-bold">Chat with {agentTitle}</h3>
              <p className="text-sm opacity-90">Your personal advisor with full memory</p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={clearChat}
              className="p-2 hover:bg-white hover:bg-opacity-20 rounded-full text-sm"
              title="Clear chat & reset plan"
            >
              🗑️
            </button>
            <button
              onClick={onClose}
              className="p-2 hover:bg-white hover:bg-opacity-20 rounded-full text-xl"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-2 text-sm">
            <strong>Error:</strong> {error}
          </div>
        )}

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50" style={{ maxHeight: 'calc(80vh - 200px)' }}>
          {isLoadingHistory ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
                <p className="text-gray-600">Loading chat history...</p>
              </div>
            </div>
          ) : messages.length === 0 ? (
            <div className="text-center text-gray-500 mt-8">
              <span className="text-4xl mb-4 block">{getAgentEmoji(agentType)}</span>
              <p className="text-lg font-medium mb-2">Hello! I'm your {agentTitle}</p>
              <p className="text-sm mb-4">I have full memory of our conversations and can update your plans in real-time!</p>
              
              {/* Sample Questions */}
              <div className="text-left max-w-md mx-auto">
                <p className="text-sm font-medium text-gray-700 mb-2">💡 Try asking:</p>
                {getSampleQuestions().map((question, index) => (
                  <button
                    key={index}
                    onClick={() => setCurrentMessage(question)}
                    className="block w-full text-left text-sm text-blue-600 hover:text-blue-800 hover:bg-blue-50 p-2 rounded mb-1 transition-colors"
                  >
                    "{question}"
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((message, index) => (
              <div key={index} className="space-y-3">
                <div className="flex justify-end">
                  <div className="bg-blue-600 text-white p-3 rounded-lg max-w-[75%] shadow-md">
                    <p className="text-sm whitespace-pre-wrap">{message.human}</p>
                    <span className="text-xs opacity-75 mt-1 block">
                      {formatTime(message.timestamp)}
                    </span>
                  </div>
                </div>
                <div className="flex justify-start">
                  <div className={`border p-3 rounded-lg max-w-[85%] shadow-md ${
                    message.isUpdate 
                      ? 'bg-green-50 border-green-200' 
                      : 'bg-white border-gray-200'
                  }`}>
                    {message.isUpdate && (
                      <div className="mb-2 text-xs text-green-600 font-medium flex items-center">
                        🔄 Plan Update Detected
                      </div>
                    )}
                    <div className="prose prose-sm text-gray-700">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.ai}</ReactMarkdown>
                    </div>
                    <span className="text-xs text-gray-500 mt-2 block">
                      {formatTime(message.timestamp)}
                    </span>
                  </div>
                </div>
              </div>
            ))
          )}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-white border border-gray-200 p-3 rounded-lg shadow-md">
                <div className="flex items-center space-x-2">
                  <div className="animate-pulse flex space-x-1">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
                  </div>
                  <span className="text-sm text-gray-600">Thinking with full memory...</span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="border-t bg-white p-4 rounded-b-lg">
          <div className="flex space-x-2">
            <textarea
              value={currentMessage}
              onChange={(e) => setCurrentMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask me anything or request plan modifications..."
              className="flex-1 border border-gray-300 rounded-lg p-3 resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              rows={2}
              disabled={isLoading}
            />
            <button
              onClick={sendMessage}
              disabled={!currentMessage.trim() || isLoading}
              className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors self-end"
            >
              {isLoading ? <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div> : '📤'}
            </button>
          </div>
          <div className="mt-2 text-xs text-gray-500 text-center">
            💡 I remember our entire conversation! Ask me to modify your plan anytime.
          </div>
          <div className="mt-1 text-xs text-gray-400 text-center">
            Enter to send • Shift+Enter for new line
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatBot;