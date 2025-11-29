/**
 * Home page with chat interface, visualizations, and threat dashboard
 */

import { useState, useEffect, useCallback } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { TrendingUp, Network, Zap } from 'lucide-react';
import ChatInterface from '../components/ChatInterface';
import Timeline from '../components/Timeline';
import KnowledgeGraph from '../components/KnowledgeGraph';
import PredictionPanel from '../components/PredictionPanel';
import { ThreatDashboard } from '../components/ThreatDashboard';
import { LiveFeed } from '../components/LiveFeed';
import { usePreferences } from '../context/PreferencesContext';
import type { ConversationResponse, Message, UserPreferencesForApi, ArticleSummary } from '../types';

function TabButton({
  active,
  onClick,
  icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-300 ${
        active
          ? 'bg-primary text-primary-foreground shadow-lg glow-border'
          : 'text-muted-foreground hover:text-foreground hover:bg-muted'
      }`}
    >
      {icon}
      {label}
    </button>
  );
}

export function HomePage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentResponse, setCurrentResponse] = useState<ConversationResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'timeline' | 'graph' | 'predictions'>('timeline');
  const [prefillMessage, setPrefillMessage] = useState<string | undefined>();
  const { preferences } = usePreferences();
  const location = useLocation();
  const navigate = useNavigate();

  // Handle incoming article state from ArticlesPage
  useEffect(() => {
    const articleRef = location.state?.askAboutArticle;
    if (articleRef) {
      // Clear state to prevent re-trigger on refresh
      navigate('/', { replace: true, state: {} });
      // Pre-fill message for user to review/edit
      setPrefillMessage(`Tell me about this article: "${articleRef.title}"`);
    }
  }, [location.state, navigate]);

  const getApiPreferences = (): UserPreferencesForApi => ({
    role: preferences.role,
    industry: preferences.industry,
    seniority: preferences.seniority,
    interests: preferences.interests,
    summary_style: preferences.summaryStyle,
    detail_level: preferences.detailLevel,
  });

  const handleSendMessage = async (message: string) => {
    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: message,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message,
          include_timeline: true,
          include_graph: true,
          include_predictions: true,
          user_preferences: getApiPreferences(),
        }),
      });

      if (!response.ok) throw new Error('Failed to get response');

      const data: ConversationResponse = await response.json();
      setCurrentResponse(data);

      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: data.response_text,
        timestamp: new Date(),
        data,
      };
      setMessages(prev => [...prev, assistantMessage]);
    } catch {
      const errorMessage: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your request. Please try again.',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSuggestionClick = (suggestion: string) => {
    handleSendMessage(suggestion);
  };

  const handleSelectArticle = useCallback((article: ArticleSummary) => {
    setPrefillMessage(`Tell me about: "${article.title}"`);
  }, []);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Threat Dashboard - Statistics at the top */}
      <ThreatDashboard />

      {/* Main Content Area */}
      <div className="flex flex-col xl:flex-row gap-6">
        {/* Live Feed - Left sidebar on xl screens */}
        <div className="xl:w-80 xl:shrink-0 h-[600px] xl:h-auto">
          <LiveFeed onSelectArticle={handleSelectArticle} />
        </div>

        {/* Main Content - Chat and Visualizations */}
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left Panel - Chat Interface */}
          <div className="lg:col-span-1">
            <ChatInterface
              messages={messages}
              isLoading={isLoading}
              onSendMessage={handleSendMessage}
              suggestions={currentResponse?.suggested_followups || [
                "Show me the latest ransomware story",
                "What vulnerabilities are trending?",
                "Analyze APT group activities",
              ]}
              onSuggestionClick={handleSuggestionClick}
              initialInput={prefillMessage}
            />
          </div>

          {/* Right Panel - Visualizations */}
          <div className="lg:col-span-1 space-y-4">
            {/* Tab Navigation */}
            <div className="flex gap-2 p-1 bg-card rounded-lg">
              <TabButton
                active={activeTab === 'timeline'}
                onClick={() => setActiveTab('timeline')}
                icon={<TrendingUp className="w-4 h-4" />}
                label="Timeline"
              />
              <TabButton
                active={activeTab === 'graph'}
                onClick={() => setActiveTab('graph')}
                icon={<Network className="w-4 h-4" />}
                label="Graph"
              />
              <TabButton
                active={activeTab === 'predictions'}
                onClick={() => setActiveTab('predictions')}
                icon={<Zap className="w-4 h-4" />}
                label="Predictions"
              />
            </div>

            <div className="bg-card rounded-xl border border-border overflow-hidden min-h-[500px]">
              {activeTab === 'timeline' && (
                <div key="timeline" className="tab-content h-full">
                  <Timeline timeline={currentResponse?.timeline} />
                </div>
              )}
              {activeTab === 'graph' && (
                <div key="graph" className="tab-content h-full">
                  <KnowledgeGraph graph={currentResponse?.graph_data} />
                </div>
              )}
              {activeTab === 'predictions' && (
                <div key="predictions" className="tab-content h-full">
                  <PredictionPanel predictions={currentResponse?.predictions} />
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
