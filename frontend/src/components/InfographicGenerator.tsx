/**
 * Infographic generator component for article visualizations
 */

import { useState } from 'react';
import {
  Image,
  RefreshCw,
  Download,
  Maximize2,
  X,
  AlertTriangle,
  Clock,
  Network,
  Shield,
  Loader2,
} from 'lucide-react';
import { useInfographics } from '../hooks/useInfographics';
import type { InfographicType } from '../types';

interface InfographicGeneratorProps {
  articleId: string;
}

interface InfographicTypeConfig {
  type: InfographicType;
  title: string;
  description: string;
  icon: React.ReactNode;
  gradient: string;
  bgColor: string;
  borderColor: string;
}

const INFOGRAPHIC_CONFIGS: InfographicTypeConfig[] = [
  {
    type: 'threat_summary',
    title: 'Threat Summary',
    description: 'Visual overview of threats, vulnerabilities, and severity levels',
    icon: <Shield className="w-6 h-6" />,
    gradient: 'from-red-500 to-rose-600',
    bgColor: 'bg-red-500/10',
    borderColor: 'border-red-500/30',
  },
  {
    type: 'timeline',
    title: 'Timeline',
    description: 'Chronological view of events and predicted developments',
    icon: <Clock className="w-6 h-6" />,
    gradient: 'from-blue-500 to-cyan-500',
    bgColor: 'bg-blue-500/10',
    borderColor: 'border-blue-500/30',
  },
  {
    type: 'knowledge_graph',
    title: 'Knowledge Graph',
    description: 'Network visualization of entities and relationships',
    icon: <Network className="w-6 h-6" />,
    gradient: 'from-purple-500 to-violet-600',
    bgColor: 'bg-purple-500/10',
    borderColor: 'border-purple-500/30',
  },
];

export default function InfographicGenerator({ articleId }: InfographicGeneratorProps) {
  const { infographics, isLoading, generate } = useInfographics(articleId);
  const [expandedImage, setExpandedImage] = useState<string | null>(null);

  if (isLoading) {
    return (
      <div className="p-8 text-center h-full flex flex-col items-center justify-center">
        <div className="w-16 h-16 mx-auto mb-4 bg-muted rounded-full flex items-center justify-center">
          <Loader2 className="w-8 h-8 text-muted-foreground animate-spin" />
        </div>
        <h3 className="text-lg font-medium text-foreground mb-2">Loading Infographics</h3>
        <p className="text-muted-foreground text-sm">Checking for existing visualizations...</p>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Image className="w-5 h-5 text-primary" />
        <h3 className="text-lg font-semibold text-foreground">AI-Generated Infographics</h3>
      </div>

      <p className="text-sm text-muted-foreground">
        Generate visual summaries and diagrams using AI. Each infographic is created based on the
        article content and related intelligence data.
      </p>

      {/* Infographic Cards */}
      <div className="grid gap-4">
        {INFOGRAPHIC_CONFIGS.map((config) => (
          <InfographicCard
            key={config.type}
            config={config}
            state={infographics[config.type]}
            onGenerate={(forceRegenerate) => generate(config.type, forceRegenerate)}
            onExpand={(url) => setExpandedImage(url)}
          />
        ))}
      </div>

      {/* Disclaimer */}
      <div className="text-xs text-muted-foreground flex items-start gap-2 p-3 bg-muted/30 rounded-lg">
        <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
        <span>
          Infographics are generated using Google Gemini AI. Generation may take 10-30 seconds.
          Results are cached for faster subsequent access.
        </span>
      </div>

      {/* Fullscreen Image Modal */}
      {expandedImage && (
        <ImageModal imageUrl={expandedImage} onClose={() => setExpandedImage(null)} />
      )}
    </div>
  );
}

interface InfographicCardProps {
  config: InfographicTypeConfig;
  state: {
    url: string | null;
    isGenerating: boolean;
    error: string | null;
  };
  onGenerate: (forceRegenerate: boolean) => Promise<unknown>;
  onExpand: (url: string) => void;
}

function InfographicCard({ config, state, onGenerate, onExpand }: InfographicCardProps) {
  const handleGenerate = async (forceRegenerate: boolean = false) => {
    await onGenerate(forceRegenerate);
  };

  const handleDownload = () => {
    if (!state.url) return;
    const link = document.createElement('a');
    link.href = state.url;
    link.download = `${config.type}-infographic.png`;
    link.target = '_blank';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div
      className={`rounded-xl border-2 ${config.borderColor} ${config.bgColor} p-5 transition-all duration-300`}
    >
      {/* Card Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div
            className={`p-2 rounded-lg bg-gradient-to-br ${config.gradient} text-white shadow-lg`}
          >
            {config.icon}
          </div>
          <div>
            <h4 className="text-lg font-semibold text-foreground">{config.title}</h4>
            <p className="text-sm text-muted-foreground">{config.description}</p>
          </div>
        </div>
      </div>

      {/* Error State */}
      {state.error && (
        <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
          <div className="flex items-center gap-2 text-red-400">
            <AlertTriangle className="w-4 h-4" />
            <span className="text-sm font-medium">Generation Failed</span>
          </div>
          <p className="text-xs text-red-400/80 mt-1">{state.error}</p>
        </div>
      )}

      {/* Content Area */}
      {state.url ? (
        <div className="space-y-3">
          {/* Image Preview */}
          <div
            className="relative group cursor-pointer rounded-lg overflow-hidden border border-border"
            onClick={() => onExpand(state.url!)}
          >
            <img
              src={state.url}
              alt={`${config.title} infographic`}
              className="w-full h-48 object-cover transition-transform duration-300 group-hover:scale-105"
            />
            <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
              <Maximize2 className="w-8 h-8 text-white" />
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-2">
            <button
              onClick={() => onExpand(state.url!)}
              className="flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium text-foreground bg-card hover:bg-muted border border-border rounded-lg transition-colors"
            >
              <Maximize2 className="w-4 h-4" />
              View Full Size
            </button>
            <button
              onClick={handleDownload}
              className="flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium text-foreground bg-card hover:bg-muted border border-border rounded-lg transition-colors"
            >
              <Download className="w-4 h-4" />
            </button>
            <button
              onClick={() => handleGenerate(true)}
              disabled={state.isGenerating}
              className="flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium text-foreground bg-card hover:bg-muted border border-border rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <RefreshCw className={`w-4 h-4 ${state.isGenerating ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {/* Empty State */}
          <div className="h-48 rounded-lg border-2 border-dashed border-border flex flex-col items-center justify-center text-center p-4">
            <Image className="w-12 h-12 text-muted-foreground mb-3" />
            <p className="text-sm text-muted-foreground">No infographic generated yet</p>
          </div>

          {/* Generate Button */}
          <button
            onClick={() => handleGenerate(false)}
            disabled={state.isGenerating}
            className={`w-full flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium text-white bg-gradient-to-r ${config.gradient} hover:opacity-90 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg`}
          >
            {state.isGenerating ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Image className="w-4 h-4" />
                Generate Infographic
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
}

interface ImageModalProps {
  imageUrl: string;
  onClose: () => void;
}

function ImageModal({ imageUrl, onClose }: ImageModalProps) {
  const handleDownload = () => {
    const link = document.createElement('a');
    link.href = imageUrl;
    link.download = 'infographic.png';
    link.target = '_blank';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="relative max-w-5xl max-h-[90vh] bg-card rounded-xl overflow-hidden shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="absolute top-0 right-0 p-4 flex gap-2 z-10">
          <button
            onClick={handleDownload}
            className="p-2 bg-black/50 hover:bg-black/70 text-white rounded-lg transition-colors"
          >
            <Download className="w-5 h-5" />
          </button>
          <button
            onClick={onClose}
            className="p-2 bg-black/50 hover:bg-black/70 text-white rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Image */}
        <img
          src={imageUrl}
          alt="Infographic full view"
          className="max-w-full max-h-[90vh] object-contain"
        />
      </div>
    </div>
  );
}
