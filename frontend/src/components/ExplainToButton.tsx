/**
 * "Explain It To..." Button Component
 * Translates threat content for different audiences (CEO, Board, Developers)
 */

import { useState } from 'react';
import { Users, Briefcase, Code, X, Loader2, AlertTriangle, CheckCircle, ChevronRight } from 'lucide-react';
import { explainToAudience } from '../services/explain';
import type { AudienceType, ExplainToResponse } from '../types';

interface ExplainToButtonProps {
  content: string;
  articleId?: string;
  predictionId?: string;
  className?: string;
}

interface AudienceOption {
  type: AudienceType;
  label: string;
  description: string;
  icon: typeof Users;
  color: string;
  bgColor: string;
  borderColor: string;
}

const audienceOptions: AudienceOption[] = [
  {
    type: 'ceo',
    label: 'CEO',
    description: 'Business impact & decisions',
    icon: Briefcase,
    color: 'text-blue-400',
    bgColor: 'bg-blue-500/10',
    borderColor: 'border-blue-500/30',
  },
  {
    type: 'board',
    label: 'Board',
    description: 'Governance & risk',
    icon: Users,
    color: 'text-purple-400',
    bgColor: 'bg-purple-500/10',
    borderColor: 'border-purple-500/30',
  },
  {
    type: 'developers',
    label: 'Developers',
    description: 'Technical details & fixes',
    icon: Code,
    color: 'text-green-400',
    bgColor: 'bg-green-500/10',
    borderColor: 'border-green-500/30',
  },
];

export default function ExplainToButton({
  content,
  articleId,
  predictionId,
  className = '',
}: ExplainToButtonProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedAudience, setSelectedAudience] = useState<AudienceType | null>(null);
  const [response, setResponse] = useState<ExplainToResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleAudienceSelect = async (audience: AudienceType) => {
    setSelectedAudience(audience);
    setIsLoading(true);
    setError(null);

    try {
      const result = await explainToAudience({
        content,
        audience,
        article_id: articleId,
        prediction_id: predictionId,
      });
      setResponse(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to translate content');
    } finally {
      setIsLoading(false);
    }
  };

  const handleClose = () => {
    setIsOpen(false);
    setResponse(null);
    setSelectedAudience(null);
    setError(null);
  };

  const riskColors = {
    critical: { bg: 'bg-red-500/20', text: 'text-red-400', border: 'border-red-500/30' },
    high: { bg: 'bg-orange-500/20', text: 'text-orange-400', border: 'border-orange-500/30' },
    medium: { bg: 'bg-yellow-500/20', text: 'text-yellow-400', border: 'border-yellow-500/30' },
    low: { bg: 'bg-green-500/20', text: 'text-green-400', border: 'border-green-500/30' },
  };

  return (
    <>
      {/* Trigger Button */}
      <button
        onClick={() => setIsOpen(true)}
        className={`inline-flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-lg
          bg-primary/10 text-primary hover:bg-primary/20 border border-primary/20
          transition-all duration-200 ${className}`}
      >
        <Users className="w-3.5 h-3.5" />
        Explain It To...
      </button>

      {/* Modal Overlay */}
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={handleClose}
          />

          {/* Modal Content */}
          <div className="relative w-full max-w-2xl max-h-[90vh] overflow-hidden rounded-xl bg-card border border-border shadow-2xl animate-scale-in">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-border">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-primary/10 rounded-lg">
                  <Users className="w-5 h-5 text-primary" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-foreground">Explain It To...</h2>
                  <p className="text-sm text-muted-foreground">
                    Translate this threat for your audience
                  </p>
                </div>
              </div>
              <button
                onClick={handleClose}
                className="p-2 rounded-lg hover:bg-muted transition-colors"
              >
                <X className="w-5 h-5 text-muted-foreground" />
              </button>
            </div>

            {/* Body */}
            <div className="p-4 overflow-y-auto max-h-[calc(90vh-8rem)]">
              {!response && !isLoading && !error && (
                <>
                  {/* Audience Selection */}
                  <p className="text-sm text-muted-foreground mb-4">
                    Select an audience to translate this security information:
                  </p>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    {audienceOptions.map((option) => (
                      <button
                        key={option.type}
                        onClick={() => handleAudienceSelect(option.type)}
                        className={`group p-4 rounded-xl border-2 ${option.borderColor} ${option.bgColor}
                          hover:scale-[1.02] transition-all duration-200 text-left`}
                      >
                        <div className="flex items-center gap-3 mb-2">
                          <div className={`p-2 rounded-lg bg-card/50`}>
                            <option.icon className={`w-5 h-5 ${option.color}`} />
                          </div>
                          <span className="font-semibold text-foreground">{option.label}</span>
                        </div>
                        <p className="text-xs text-muted-foreground">{option.description}</p>
                        <div className="mt-3 flex items-center gap-1 text-xs text-muted-foreground group-hover:text-foreground transition-colors">
                          <span>Translate</span>
                          <ChevronRight className="w-3 h-3" />
                        </div>
                      </button>
                    ))}
                  </div>

                  {/* Original Content Preview */}
                  <div className="mt-6 p-3 rounded-lg bg-muted/30 border border-border">
                    <p className="text-xs text-muted-foreground uppercase tracking-wide mb-2">
                      Original Content
                    </p>
                    <p className="text-sm text-foreground/80 line-clamp-3">{content}</p>
                  </div>
                </>
              )}

              {/* Loading State */}
              {isLoading && (
                <div className="py-12 text-center">
                  <Loader2 className="w-8 h-8 mx-auto mb-4 text-primary animate-spin" />
                  <p className="text-sm text-muted-foreground">
                    Translating for {selectedAudience?.toUpperCase()}...
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    AI is adapting the content for your audience
                  </p>
                </div>
              )}

              {/* Error State */}
              {error && (
                <div className="py-8 text-center">
                  <div className="w-12 h-12 mx-auto mb-4 bg-red-500/10 rounded-full flex items-center justify-center">
                    <AlertTriangle className="w-6 h-6 text-red-400" />
                  </div>
                  <p className="text-foreground font-medium mb-2">Translation Failed</p>
                  <p className="text-sm text-muted-foreground mb-4">{error}</p>
                  <button
                    onClick={() => {
                      setError(null);
                      setSelectedAudience(null);
                    }}
                    className="px-4 py-2 text-sm rounded-lg bg-muted hover:bg-muted/80 transition-colors"
                  >
                    Try Again
                  </button>
                </div>
              )}

              {/* Response Display */}
              {response && (
                <div className="space-y-4">
                  {/* Audience Badge & Risk Level */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {audienceOptions.find((o) => o.type === response.audience)?.icon && (
                        <div
                          className={`p-1.5 rounded-lg ${
                            audienceOptions.find((o) => o.type === response.audience)?.bgColor
                          }`}
                        >
                          {(() => {
                            const Icon = audienceOptions.find((o) => o.type === response.audience)?.icon;
                            return Icon ? (
                              <Icon
                                className={`w-4 h-4 ${
                                  audienceOptions.find((o) => o.type === response.audience)?.color
                                }`}
                              />
                            ) : null;
                          })()}
                        </div>
                      )}
                      <span className="font-medium text-foreground">
                        For {response.audience.toUpperCase()}
                      </span>
                    </div>
                    <span
                      className={`px-2.5 py-1 rounded-full text-xs font-bold uppercase ${
                        riskColors[response.risk_level]?.bg
                      } ${riskColors[response.risk_level]?.text} ${
                        riskColors[response.risk_level]?.border
                      } border`}
                    >
                      {response.risk_level} Risk
                    </span>
                  </div>

                  {/* Translated Content */}
                  <div className="p-4 rounded-xl bg-primary/5 border border-primary/20">
                    <p className="text-foreground leading-relaxed">{response.translated_content}</p>
                  </div>

                  {/* Business Impact */}
                  {response.business_impact && (
                    <div className="p-3 rounded-lg bg-muted/30 border border-border">
                      <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">
                        Business Impact
                      </p>
                      <p className="text-sm text-foreground">{response.business_impact}</p>
                    </div>
                  )}

                  {/* Key Points */}
                  {response.key_points.length > 0 && (
                    <div>
                      <p className="text-xs text-muted-foreground uppercase tracking-wide mb-2">
                        Key Points
                      </p>
                      <ul className="space-y-2">
                        {response.key_points.map((point, idx) => (
                          <li key={idx} className="flex items-start gap-2 text-sm">
                            <CheckCircle className="w-4 h-4 text-green-400 mt-0.5 flex-shrink-0" />
                            <span className="text-foreground/90">{point}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Recommended Actions */}
                  {response.recommended_actions.length > 0 && (
                    <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20">
                      <p className="text-xs text-amber-400 uppercase tracking-wide mb-2 font-medium">
                        Recommended Actions
                      </p>
                      <ul className="space-y-2">
                        {response.recommended_actions.map((action, idx) => (
                          <li key={idx} className="flex items-start gap-2 text-sm">
                            <span className="text-amber-400 font-bold">{idx + 1}.</span>
                            <span className="text-foreground/90">{action}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Back Button */}
                  <button
                    onClick={() => {
                      setResponse(null);
                      setSelectedAudience(null);
                    }}
                    className="w-full mt-2 px-4 py-2.5 text-sm rounded-lg bg-muted hover:bg-muted/80
                      transition-colors text-center"
                  >
                    Translate for Another Audience
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
