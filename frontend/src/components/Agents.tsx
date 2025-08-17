import React, { useState, useEffect } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import ChatBot from './ChatBot';

interface AgentsProps {
  userId: number;
}

type PlanName = 'HealthSummary' | 'FitnessTrainer' | 'Nutritionist' | 'HealthAdvisor';

interface PlanInfo {
  content: string;
  is_updated: boolean;
  modifications?: string;
}

interface Plans {
  HealthSummary?: PlanInfo;
  FitnessTrainer?: PlanInfo;
  Nutritionist?: PlanInfo;
  HealthAdvisor?: PlanInfo;
}

interface UpdateHistory {
  summary: string;
  timestamp: string;
  preview: string;
}

const Agents: React.FC<AgentsProps> = ({ userId }) => {
  const [plans, setPlans] = useState<Plans | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isHistoryLoading, setIsHistoryLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const [openPanels, setOpenPanels] = useState<Record<PlanName, boolean>>({
    HealthSummary: false,
    FitnessTrainer: false,
    Nutritionist: false,
    HealthAdvisor: false,
  });

  // Chat bot states
  const [activeChatBot, setActiveChatBot] = useState<PlanName | null>(null);
  
  // Update history states
  const [showUpdateHistory, setShowUpdateHistory] = useState<Record<PlanName, boolean>>({
    HealthSummary: false,
    FitnessTrainer: false,
    Nutritionist: false,
    HealthAdvisor: false,
  });
  const [updateHistories, setUpdateHistories] = useState<Record<PlanName, UpdateHistory[]>>({
    HealthSummary: [],
    FitnessTrainer: [],
    Nutritionist: [],
    HealthAdvisor: [],
  });

  const togglePanel = (panelName: PlanName) => {
    setOpenPanels(prev => ({ ...prev, [panelName]: !prev[panelName] }));
  };

  const openChatBot = (agentType: PlanName) => {
    setActiveChatBot(agentType);
  };

  const closeChatBot = () => {
    setActiveChatBot(null);
    // Refresh current plans when chat closes (in case updates were made)
    fetchCurrentPlans();
  };

  const toggleUpdateHistory = async (planName: PlanName) => {
    if (!showUpdateHistory[planName]) {
      // Load update history
      try {
        const response = await axios.post('http://localhost:5000/api/plan-updates-history', {
          userId,
          agentType: planName
        });
        setUpdateHistories(prev => ({
          ...prev,
          [planName]: response.data.updates || []
        }));
      } catch (err) {
        console.error("Could not fetch update history:", err);
      }
    }
    
    setShowUpdateHistory(prev => ({ ...prev, [planName]: !prev[planName] }));
  };

  const resetToOriginal = async (planName: PlanName) => {
    if (window.confirm(`Are you sure you want to reset ${getAgentTitle(planName)} plan to the original version? This will remove all updates and chat history.`)) {
      try {
        await axios.post('http://localhost:5000/api/reset-to-original', {
          userId,
          agentType: planName
        });
        
        // Refresh plans
        await fetchCurrentPlans();
        setSuccessMessage(`${getAgentTitle(planName)} plan has been reset to original version! 🔄`);
        setTimeout(() => setSuccessMessage(null), 5000);
      } catch (err: any) {
        setError(err.response?.data?.error || 'Failed to reset plan.');
      }
    }
  };

  const fetchCurrentPlans = async () => {
    if (!userId) return;
    try {
      const response = await axios.post('http://localhost:5000/api/get-current-plans', { userId });
      if (response.data && Object.keys(response.data).length > 0) {
        setPlans(response.data);
      }
    } catch (err) {
      console.error("Could not fetch current plans:", err);
    }
  };

  useEffect(() => {
    const fetchHistory = async () => {
      if (!userId) return;
      try {
        // First try to get current plans (which include updates)
        await fetchCurrentPlans();
        
        // If no current plans, try to get original history
        if (!plans) {
          const response = await axios.post('http://localhost:5000/api/get-history', { userId });
          if (response.data && Object.keys(response.data).length > 0) {
            // Convert old format to new format
            const convertedPlans: Plans = {};
            Object.keys(response.data).forEach(key => {
              const planName = key as PlanName;
              convertedPlans[planName] = {
                content: response.data[key],
                is_updated: false
              };
            });
            setPlans(convertedPlans);
          }
        }
      } catch (err) {
        console.error("Could not fetch plan history:", err);
      } finally {
        setIsHistoryLoading(false);
      }
    };
    fetchHistory();
  }, [userId]);

  const handleGeneratePlan = async () => {
    setIsGenerating(true);
    setError(null);
    setSuccessMessage(null);
    try {
      const response = await axios.post('http://localhost:5000/api/generate-plan', { userId });
      
      // Convert old format to new format
      const convertedPlans: Plans = {};
      Object.keys(response.data).forEach(key => {
        const planName = key as PlanName;
        convertedPlans[planName] = {
          content: response.data[key],
          is_updated: false
        };
      });
      
      setPlans(convertedPlans);
      setOpenPanels({
        HealthSummary: false,
        FitnessTrainer: false,
        Nutritionist: false,
        HealthAdvisor: false,
      });
      setSuccessMessage("Your new personalized plans have been successfully generated! 🎉");
      setTimeout(() => setSuccessMessage(null), 5000);
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to generate new plans.');
    } finally {
      setIsGenerating(false);
    }
  };

  const getAgentTitle = (planName: PlanName): string => {
    const titles = {
      'HealthSummary': 'Health Analyst',
      'FitnessTrainer': 'Fitness Trainer',
      'Nutritionist': 'Nutritionist',
      'HealthAdvisor': 'Health Advisor'
    };
    return titles[planName];
  };

  const getUpdateStatusBadge = (planInfo: PlanInfo) => {
    if (planInfo.is_updated) {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 ml-2">
          🔄 Updated
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 ml-2">
        🆕 Original
      </span>
    );
  };

  const renderCollapsiblePlan = (planName: PlanName, title: string, emoji: string) => {
    const planInfo = plans?.[planName];
    const isOpen = openPanels[planName];
    const historyOpen = showUpdateHistory[planName];
    const updates = updateHistories[planName] || [];
    
    if (!planInfo) return null;

    return (
      <div className="bg-white rounded-lg shadow-md mb-4 overflow-hidden transition-all duration-300">
        <button 
          onClick={() => togglePanel(planName)} 
          className="w-full flex justify-between items-center p-4 sm:p-6 text-left hover:bg-gray-50 transition-colors"
        >
          <h2 className="text-xl sm:text-2xl font-bold text-gray-800 flex items-center">
            <span className="mr-3">{emoji}</span>
            {title}
            {getUpdateStatusBadge(planInfo)}
          </h2>
          <span className={`transform transition-transform duration-300 text-2xl text-gray-500 ${isOpen ? 'rotate-180' : ''}`}>
            ▼
          </span>
        </button>

        <div className={`transition-all duration-500 ease-in-out ${isOpen ? 'max-h-[50rem]' : 'max-h-0'} overflow-y-auto`}>
          <div className="prose prose-lg max-w-none text-gray-700 p-4 sm:p-6 pt-0">
            {/* Update info banner */}
            {planInfo.is_updated && planInfo.modifications && (
              <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-4">
                <div className="flex items-start">
                  <span className="text-green-400 mr-2">🔄</span>
                  <div>
                    <h4 className="text-green-800 font-medium mb-1">Plan Updated!</h4>
                    <p className="text-green-700 text-sm">{planInfo.modifications}</p>
                  </div>
                </div>
              </div>
            )}

            <ReactMarkdown remarkPlugins={[remarkGfm]}>{planInfo.content}</ReactMarkdown>
            
            {/* Action Buttons */}
            <div className="mt-6 pt-4 border-t border-gray-200 space-y-3">
              <div className="flex flex-wrap gap-3">
                <button
                  onClick={() => openChatBot(planName)}
                  className="inline-flex items-center px-4 py-2 bg-gradient-to-r from-blue-500 to-purple-600 text-white font-medium rounded-lg hover:from-blue-600 hover:to-purple-700 transition-all duration-200 shadow-md hover:shadow-lg transform hover:scale-105"
                >
                  <span className="mr-2">💬</span>
                  Chat with {getAgentTitle(planName)}
                </button>
                
                <button
                  onClick={() => toggleUpdateHistory(planName)}
                  className="inline-flex items-center px-4 py-2 bg-gray-500 text-white font-medium rounded-lg hover:bg-gray-600 transition-all duration-200 shadow-md"
                >
                  <span className="mr-2">📋</span>
                  {historyOpen ? 'Hide' : 'Show'} Update History
                </button>
                
                {planInfo.is_updated && (
                  <button
                    onClick={() => resetToOriginal(planName)}
                    className="inline-flex items-center px-4 py-2 bg-orange-500 text-white font-medium rounded-lg hover:bg-orange-600 transition-all duration-200 shadow-md"
                  >
                    <span className="mr-2">↩️</span>
                    Reset to Original
                  </button>
                )}
              </div>
              
              <p className="text-sm text-gray-600">
                💡 Have a question or want to modify these recommendations? Chat with your personal advisor!
              </p>
            </div>

            {/* Update History Section */}
            {historyOpen && (
              <div className="mt-6 pt-4 border-t border-gray-200">
                <h4 className="text-lg font-semibold text-gray-800 mb-3">📋 Update History</h4>
                {updates.length === 0 ? (
                  <p className="text-gray-500 italic">No updates made yet. Start chatting to customize your plan!</p>
                ) : (
                  <div className="space-y-3">
                    {updates.map((update, index) => (
                      <div key={index} className="bg-gray-50 rounded-lg p-3 border">
                        <div className="flex justify-between items-start mb-2">
                          <span className="text-sm font-medium text-gray-700">Update #{updates.length - index}</span>
                          <span className="text-xs text-gray-500">
                            {new Date(update.timestamp).toLocaleString()}
                          </span>
                        </div>
                        <p className="text-sm text-gray-600 mb-2">{update.summary}</p>
                        <p className="text-xs text-gray-500 italic">{update.preview}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  if (isHistoryLoading) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-green-600 mx-auto mb-4"></div>
          <p className="text-xl text-gray-600">Loading your dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4 sm:p-8 bg-gray-50 min-h-screen">
      <div className="text-center mb-8">
        <h1 className="text-4xl font-extrabold text-gray-900 mb-4">
          Your Personalized Health Dashboard
        </h1>
        <p className="mt-4 text-lg text-gray-600 max-w-2xl mx-auto">
          Ready to start your health journey? Generate or review your personalized plans from our expert advisors.
          💡 <strong>New!</strong> Chat with any advisor to update and customize your plans in real-time!
        </p>
        <button 
          onClick={handleGeneratePlan} 
          disabled={isGenerating} 
          className="mt-6 px-8 py-3 bg-green-600 text-white font-semibold rounded-lg shadow-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-opacity-75 transition duration-300 disabled:bg-gray-400 disabled:cursor-not-allowed"
        >
          {isGenerating ? (
            <span className="flex items-center">
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
              Generating plans...
            </span>
          ) : (
            plans ? '🚀 Regenerate my plan!' : '🚀 Get my first plan!'
          )}
        </button>
      </div>

      <div className="max-w-3xl mx-auto mb-6 h-12">
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-lg relative text-center animate-fade-in" role="alert">
            <strong>Error:</strong> {error}
          </div>
        )}
        {successMessage && (
          <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded-lg relative text-center animate-fade-in" role="alert">
            <strong>{successMessage}</strong>
          </div>
        )}
      </div>

      {!isGenerating && !plans && (
        <div className="text-center text-gray-500 mt-8 p-6 bg-white rounded-lg shadow-md">
          <div className="text-6xl mb-4">🏥</div>
          <p className="text-xl font-medium mb-2">Welcome, it looks like you don't have a plan yet.</p>
          <p>Click the button above to generate your first set of personalized health recommendations!</p>
        </div>
      )}
      
      {plans && (
        <div className="max-w-3xl mx-auto">
          {renderCollapsiblePlan('HealthSummary', 'Current Health Summary', '📊')}
          {renderCollapsiblePlan('FitnessTrainer', 'Fitness Trainer Plan', '🏋️')}
          {renderCollapsiblePlan('Nutritionist', 'Nutritionist Plan', '🥗')}
          {renderCollapsiblePlan('HealthAdvisor', 'Health Advisor Plan', '❤️')}
        </div>
      )}

      {/* Chat Bot Component */}
      {activeChatBot && (
        <ChatBot
          userId={userId}
          agentType={activeChatBot}
          agentTitle={getAgentTitle(activeChatBot)}
          isVisible={activeChatBot !== null}
          onClose={closeChatBot}
        />
      )}
    </div>
  );
};

export default Agents;