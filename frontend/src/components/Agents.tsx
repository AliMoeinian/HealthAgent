import React, { useState, useEffect } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface AgentsProps {
  userId: number;
}

type PlanName = 'HealthSummary' | 'FitnessTrainer' | 'Nutritionist' | 'HealthAdvisor';

interface Plans {
  HealthSummary?: string;
  FitnessTrainer?: string;
  Nutritionist?: string;
  HealthAdvisor?: string;
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

  const togglePanel = (panelName: PlanName) => {
    setOpenPanels(prev => ({ ...prev, [panelName]: !prev[panelName] }));
  };

  useEffect(() => {
    const fetchHistory = async () => {
      if (!userId) return;
      try {
        const response = await axios.post('http://localhost:5000/api/get-history', { userId });
        if (response.data && Object.keys(response.data).length > 0) {
          setPlans(response.data);
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
      setPlans(response.data);
      setOpenPanels({
        HealthSummary: false,
        FitnessTrainer: false,
        Nutritionist: false,
        HealthAdvisor: false,
      });
      setSuccessMessage("Your new personalized plans have been generated successfully!");
      setTimeout(() => setSuccessMessage(null), 5000);
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to generate new plans.');
    } finally {
      setIsGenerating(false);
    }
  };

  const renderCollapsiblePlan = (planName: PlanName, title: string) => {
    const content = plans?.[planName];
    const isOpen = openPanels[planName];
    if (!content) return null;

    return (
      <div className="bg-white rounded-lg shadow-md mb-4 overflow-hidden transition-all duration-300">
        <button onClick={() => togglePanel(planName)} className="w-full flex justify-between items-center p-4 sm:p-6 text-left">
          <h2 className="text-xl sm:text-2xl font-bold text-gray-800">{title}</h2>
          <span className={`transform transition-transform duration-300 text-2xl text-gray-500 ${isOpen ? 'rotate-180' : ''}`}>▼</span>
        </button>

        {/* FIX: The change is in the line below */}
        <div className={`transition-all duration-500 ease-in-out ${isOpen ? 'max-h-[40rem]' : 'max-h-0'} overflow-y-auto`}>
          <div className="prose prose-lg max-w-none text-gray-700 p-4 sm:p-6 pt-0">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
          </div>
        </div>
      </div>
    );
  };

  if (isHistoryLoading) {
    return <div className="flex justify-center items-center h-screen"><p className="text-xl">Loading your dashboard...</p></div>;
  }

  return (
    <div className="container mx-auto p-4 sm:p-8 bg-gray-50 min-h-screen">
      <div className="text-center mb-8">
        <h1 className="text-4xl font-extrabold text-gray-900">Your Personalized Health Dashboard</h1>
        <p className="mt-4 text-lg text-gray-600">
          Ready to start your health journey? Generate or review your personalized plans from our expert agents.
        </p>
        <button onClick={handleGeneratePlan} disabled={isGenerating} className="mt-6 px-8 py-3 bg-green-600 text-white font-semibold rounded-lg shadow-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-opacity-75 transition duration-300 disabled:bg-gray-400 disabled:cursor-not-allowed">
          {isGenerating ? 'Generating Plans...' : (plans ? '🚀 Regenerate My Plan!' : '🚀 Get My First Plan!')}
        </button>
      </div>

      <div className="max-w-3xl mx-auto mb-6 h-12">
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-lg relative text-center" role="alert">
            <strong>Error:</strong> {error}
          </div>
        )}
        {successMessage && (
          <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded-lg relative text-center" role="alert">
            <strong>{successMessage}</strong>
          </div>
        )}
      </div>

      {!isGenerating && !plans && (
        <div className="text-center text-gray-500 mt-8 p-6 bg-white rounded-lg shadow-md">
          <p className="text-xl">Welcome, it looks like you don't have a plan yet.</p>
          <p>Click the button above to generate your first set of personalized health recommendations!</p>
        </div>
      )}
      
      {plans && (
        <div className="max-w-3xl mx-auto">
          {renderCollapsiblePlan('HealthSummary', '📊 Current Health Snapshot')}
          {renderCollapsiblePlan('FitnessTrainer', '🏋️ Fitness Trainer Plan')}
          {renderCollapsiblePlan('Nutritionist', '🥗 Nutritionist Plan')}
          {renderCollapsiblePlan('HealthAdvisor', '❤️ Health Advisor Plan')}
        </div>
      )}
    </div>
  );
};

export default Agents;