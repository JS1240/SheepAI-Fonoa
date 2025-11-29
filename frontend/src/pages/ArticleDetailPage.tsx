/**
 * Article detail page with graph and timeline visualizations
 */

import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Calendar, ExternalLink, Network, TrendingUp, AlertTriangle, Shield, MessageSquare, Image, Clock, Dna } from 'lucide-react';
import { useArticle } from '../hooks/useArticle';
import KnowledgeGraph from '../components/KnowledgeGraph';
import Timeline from '../components/Timeline';
import InfographicGenerator from '../components/InfographicGenerator';
import ThreatForecast from '../components/ThreatForecast';
import ThreatDNA from '../components/ThreatDNA';
import { PageLoader } from '../components/common/LoadingSpinner';
import { PageError } from '../components/common/ErrorMessage';

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
      className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
        active
          ? 'bg-primary text-primary-foreground shadow-lg'
          : 'text-muted-foreground hover:text-foreground hover:bg-muted'
      }`}
    >
      {icon}
      {label}
    </button>
  );
}

export function ArticleDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'details' | 'graph' | 'timeline' | 'forecast' | 'dna' | 'infographics'>('details');

  const { article, connections, timeline, isLoading, error, refetch } = useArticle(id);

  if (isLoading) {
    return <PageLoader message="Loading article..." />;
  }

  if (error || !article) {
    return (
      <PageError
        title="Failed to load article"
        message={error?.message || 'Article not found'}
        onRetry={refetch}
      />
    );
  }

  const formattedDate = new Date(article.published_at).toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });

  return (
    <div className="space-y-6">
      {/* Back Navigation */}
      <button
        onClick={() => navigate('/articles')}
        className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Articles
      </button>

      {/* Article Header */}
      <div className="bg-card rounded-xl border border-border p-6">
        <h1 className="text-2xl font-bold text-foreground mb-4">{article.title}</h1>

        {/* Meta Information */}
        <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground mb-4">
          <div className="flex items-center gap-1.5">
            <Calendar className="w-4 h-4" />
            {formattedDate}
          </div>
          <a
            href={article.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 text-primary hover:text-primary/80 transition-colors"
          >
            <ExternalLink className="w-4 h-4" />
            View Source
          </a>
          <button
            onClick={() => navigate('/', {
              state: {
                askAboutArticle: {
                  id: article.id,
                  title: article.title,
                  summary: article.summary,
                }
              }
            })}
            className="flex items-center gap-1.5 text-primary hover:text-primary/80 transition-colors"
          >
            <MessageSquare className="w-4 h-4" />
            Ask AI about this
          </button>
        </div>

        {/* Categories */}
        {article.categories && article.categories.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-4">
            {article.categories.map((category) => (
              <span
                key={category}
                className="px-3 py-1 text-sm rounded-full bg-primary/20 text-primary border border-primary/30"
              >
                {category}
              </span>
            ))}
          </div>
        )}

        {/* Vulnerabilities */}
        {article.vulnerabilities && article.vulnerabilities.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-4">
            {article.vulnerabilities.map((vuln) => (
              <span
                key={vuln}
                className="flex items-center gap-1.5 px-3 py-1 text-sm rounded-full bg-threat-critical/20 text-threat-critical border border-threat-critical/30"
              >
                <AlertTriangle className="w-3.5 h-3.5" />
                {vuln}
              </span>
            ))}
          </div>
        )}

        {/* Threat Actors */}
        {article.threat_actors && article.threat_actors.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {article.threat_actors.map((actor) => (
              <span
                key={actor}
                className="flex items-center gap-1.5 px-3 py-1 text-sm rounded-full bg-purple-600/20 text-purple-400 border border-purple-600/30"
              >
                <Shield className="w-3.5 h-3.5" />
                {actor}
              </span>
            ))}
          </div>
        )}

        {/* Summary */}
        {article.summary && (
          <div className="mt-4 pt-4 border-t border-border">
            <p className="text-foreground/80 leading-relaxed">{article.summary}</p>
          </div>
        )}
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-2 p-1 bg-card rounded-lg w-fit">
        <TabButton
          active={activeTab === 'details'}
          onClick={() => setActiveTab('details')}
          icon={<Shield className="w-4 h-4" />}
          label="Details"
        />
        <TabButton
          active={activeTab === 'graph'}
          onClick={() => setActiveTab('graph')}
          icon={<Network className="w-4 h-4" />}
          label="Knowledge Graph"
        />
        <TabButton
          active={activeTab === 'timeline'}
          onClick={() => setActiveTab('timeline')}
          icon={<TrendingUp className="w-4 h-4" />}
          label="Timeline"
        />
        <TabButton
          active={activeTab === 'forecast'}
          onClick={() => setActiveTab('forecast')}
          icon={<Clock className="w-4 h-4" />}
          label="48h Forecast"
        />
        <TabButton
          active={activeTab === 'dna'}
          onClick={() => setActiveTab('dna')}
          icon={<Dna className="w-4 h-4" />}
          label="Threat DNA"
        />
        <TabButton
          active={activeTab === 'infographics'}
          onClick={() => setActiveTab('infographics')}
          icon={<Image className="w-4 h-4" />}
          label="Infographics"
        />
      </div>

      {/* Tab Content */}
      <div className="bg-card rounded-xl border border-border overflow-hidden min-h-[500px]">
        {activeTab === 'details' && (
          <div className="p-6">
            <h3 className="text-lg font-semibold text-foreground mb-4">Full Content</h3>
            {article.content ? (
              <div className="prose prose-invert max-w-none dark:prose-invert">
                <p className="text-foreground/80 whitespace-pre-wrap leading-relaxed">
                  {article.content}
                </p>
              </div>
            ) : (
              <p className="text-muted-foreground">No detailed content available for this article.</p>
            )}
          </div>
        )}
        {activeTab === 'graph' && (
          <KnowledgeGraph graph={connections || undefined} />
        )}
        {activeTab === 'timeline' && (
          <Timeline timeline={timeline || undefined} />
        )}
        {activeTab === 'forecast' && id && (
          <ThreatForecast articleId={id} />
        )}
        {activeTab === 'dna' && id && (
          <ThreatDNA articleId={id} />
        )}
        {activeTab === 'infographics' && id && (
          <InfographicGenerator articleId={id} />
        )}
      </div>
    </div>
  );
}
