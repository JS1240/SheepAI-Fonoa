/**
 * Threat DNA Matching Component
 * Displays historical pattern matching and threat analysis
 */

import { useState, useEffect } from 'react';
import { Dna, AlertTriangle, Shield, Target, Loader2, ChevronDown, ChevronUp, History, Zap, Users } from 'lucide-react';
import { getThreatDNA } from '../services/dna';
import type { ThreatDNA as ThreatDNAType, DNAMatch } from '../types';

interface ThreatDNAProps {
  articleId: string;
  className?: string;
}

const MATCH_STRENGTH_COLORS = {
  STRONG: { bg: 'bg-red-500/20', text: 'text-red-400', border: 'border-red-500/30', bar: 'bg-red-500' },
  MODERATE: { bg: 'bg-orange-500/20', text: 'text-orange-400', border: 'border-orange-500/30', bar: 'bg-orange-500' },
  WEAK: { bg: 'bg-yellow-500/20', text: 'text-yellow-400', border: 'border-yellow-500/30', bar: 'bg-yellow-500' },
  PARTIAL: { bg: 'bg-blue-500/20', text: 'text-blue-400', border: 'border-blue-500/30', bar: 'bg-blue-500' },
};

function DNAMatchCard({ match, index }: { match: DNAMatch; index: number }) {
  const [isExpanded, setIsExpanded] = useState(index === 0);
  const colors = MATCH_STRENGTH_COLORS[match.match_strength];

  return (
    <div className={`rounded-lg border ${colors.border} overflow-hidden`}>
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className={`w-full p-4 ${colors.bg} flex items-center justify-between hover:opacity-90 transition-opacity`}
      >
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <History className={`w-4 h-4 ${colors.text}`} />
            <span className="font-medium text-foreground">{match.historical_title}</span>
          </div>
          <span className={`px-2 py-0.5 rounded text-xs font-bold ${colors.text}`}>
            {Math.round(match.similarity_score * 100)}% Match
          </span>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4 text-muted-foreground" />
        ) : (
          <ChevronDown className="w-4 h-4 text-muted-foreground" />
        )}
      </button>

      {isExpanded && (
        <div className="p-4 space-y-4 bg-card/50">
          {/* Match strength bar */}
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-muted-foreground">Similarity</span>
              <span className={colors.text}>{match.match_strength}</span>
            </div>
            <div className="h-2 bg-muted rounded-full overflow-hidden">
              <div
                className={`h-full ${colors.bar} transition-all`}
                style={{ width: `${match.similarity_score * 100}%` }}
              />
            </div>
          </div>

          {/* Historical outcome */}
          {match.historical_outcome && (
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">What Happened</p>
              <p className="text-sm text-foreground/90">{match.historical_outcome}</p>
            </div>
          )}

          {/* Matching attributes */}
          {match.matching_attributes.length > 0 && (
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wide mb-2">Matching Factors</p>
              <div className="flex flex-wrap gap-1.5">
                {match.matching_attributes.map((attr, i) => (
                  <span
                    key={i}
                    className="px-2 py-0.5 bg-primary/10 text-primary text-xs rounded"
                  >
                    {attr}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Shared elements */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {match.shared_threat_actors.length > 0 && (
              <div>
                <p className="text-xs text-muted-foreground mb-1 flex items-center gap-1">
                  <Users className="w-3 h-3" /> Threat Actors
                </p>
                <div className="flex flex-wrap gap-1">
                  {match.shared_threat_actors.map((actor, i) => (
                    <span key={i} className="px-1.5 py-0.5 bg-red-500/10 text-red-400 text-xs rounded">
                      {actor}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {match.shared_vulnerabilities.length > 0 && (
              <div>
                <p className="text-xs text-muted-foreground mb-1 flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3" /> Vulnerabilities
                </p>
                <div className="flex flex-wrap gap-1">
                  {match.shared_vulnerabilities.map((vuln, i) => (
                    <span key={i} className="px-1.5 py-0.5 bg-orange-500/10 text-orange-400 text-xs rounded">
                      {vuln}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {match.shared_techniques.length > 0 && (
              <div>
                <p className="text-xs text-muted-foreground mb-1 flex items-center gap-1">
                  <Zap className="w-3 h-3" /> Techniques
                </p>
                <div className="flex flex-wrap gap-1">
                  {match.shared_techniques.map((tech, i) => (
                    <span key={i} className="px-1.5 py-0.5 bg-purple-500/10 text-purple-400 text-xs rounded">
                      {tech}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Lessons learned */}
          {match.lessons_learned.length > 0 && (
            <div className="pt-2 border-t border-border">
              <p className="text-xs text-amber-400 uppercase tracking-wide mb-2">Lessons Learned</p>
              <ul className="space-y-1">
                {match.lessons_learned.map((lesson, i) => (
                  <li key={i} className="text-sm text-foreground/90 flex items-start gap-2">
                    <span className="text-amber-400 mt-1">-</span>
                    {lesson}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function ThreatDNA({ articleId, className = '' }: ThreatDNAProps) {
  const [dna, setDna] = useState<ThreatDNAType | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showDefenses, setShowDefenses] = useState(false);

  useEffect(() => {
    if (articleId) {
      loadDNA();
    }
  }, [articleId]);

  const loadDNA = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getThreatDNA(articleId);
      setDna(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load DNA analysis');
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className={`bg-card rounded-xl border border-border p-6 ${className}`}>
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-8 h-8 text-primary animate-spin" />
          <span className="ml-3 text-muted-foreground">Analyzing threat DNA patterns...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`bg-card rounded-xl border border-border p-6 ${className}`}>
        <div className="text-center py-8">
          <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-3" />
          <p className="text-foreground font-medium">Failed to load DNA analysis</p>
          <p className="text-sm text-muted-foreground mt-1">{error}</p>
          <button
            onClick={loadDNA}
            className="mt-4 px-4 py-2 text-sm bg-muted hover:bg-muted/80 rounded-lg transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  if (!dna) {
    return null;
  }

  return (
    <div className={`bg-card rounded-xl border border-border overflow-hidden ${className}`}>
      {/* Header */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-500/10 rounded-lg">
              <Dna className="w-5 h-5 text-purple-400" />
            </div>
            <div>
              <h3 className="font-semibold text-foreground">Threat DNA Analysis</h3>
              <p className="text-sm text-muted-foreground">{dna.threat_name}</p>
            </div>
          </div>
          {dna.has_strong_precedent && (
            <span className="px-3 py-1 rounded-full text-xs font-bold uppercase bg-red-500/20 text-red-400 border border-red-500/30">
              Strong Precedent
            </span>
          )}
        </div>
      </div>

      {/* Threat Profile */}
      <div className="p-4 bg-muted/30 grid grid-cols-2 md:grid-cols-4 gap-4">
        <div>
          <p className="text-xs text-muted-foreground">Threat Type</p>
          <p className="text-sm font-medium text-foreground">{dna.threat_type || 'Unknown'}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Attack Vector</p>
          <p className="text-sm font-medium text-foreground">{dna.attack_vector || 'Unknown'}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Top Match</p>
          <p className="text-sm font-medium text-foreground">{Math.round(dna.top_match_score * 100)}%</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Confidence</p>
          <p className="text-sm font-medium text-foreground">{Math.round(dna.confidence * 100)}%</p>
        </div>
      </div>

      {/* Summary */}
      <div className="p-4 border-b border-border">
        <p className="text-sm text-foreground leading-relaxed">{dna.summary}</p>
      </div>

      {/* Target Sectors & Techniques */}
      <div className="p-4 border-b border-border">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {dna.target_sectors.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-2">
                <Target className="w-4 h-4 text-amber-400" />
                <span className="text-sm font-medium text-foreground">Target Sectors</span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {dna.target_sectors.map((sector, i) => (
                  <span key={i} className="px-2 py-0.5 bg-amber-500/10 text-amber-400 text-xs rounded">
                    {sector}
                  </span>
                ))}
              </div>
            </div>
          )}
          {dna.techniques.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-2">
                <Zap className="w-4 h-4 text-purple-400" />
                <span className="text-sm font-medium text-foreground">MITRE ATT&CK</span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {dna.techniques.map((tech, i) => (
                  <span key={i} className="px-2 py-0.5 bg-purple-500/10 text-purple-400 text-xs rounded font-mono">
                    {tech}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Historical Matches */}
      {dna.matches.length > 0 && (
        <div className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <History className="w-4 h-4 text-muted-foreground" />
            <span className="text-sm font-medium text-foreground">Historical Pattern Matches</span>
            <span className="text-xs text-muted-foreground">({dna.matches.length} found)</span>
          </div>
          <div className="space-y-3">
            {dna.matches.map((match, idx) => (
              <DNAMatchCard key={match.match_id} match={match} index={idx} />
            ))}
          </div>
        </div>
      )}

      {/* Risk Assessment */}
      {dna.risk_assessment && (
        <div className="p-4 bg-red-500/10 border-t border-red-500/20">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className="w-4 h-4 text-red-400" />
            <span className="text-sm font-medium text-red-400">Risk Assessment</span>
          </div>
          <p className="text-sm text-foreground/90">{dna.risk_assessment}</p>
        </div>
      )}

      {/* Recommended Defenses */}
      {dna.recommended_defenses.length > 0 && (
        <div className="p-4 bg-green-500/10 border-t border-green-500/20">
          <button
            onClick={() => setShowDefenses(!showDefenses)}
            className="w-full flex items-center justify-between"
          >
            <div className="flex items-center gap-2">
              <Shield className="w-4 h-4 text-green-400" />
              <span className="text-sm font-medium text-green-400">Recommended Defenses</span>
              <span className="text-xs text-muted-foreground">({dna.recommended_defenses.length})</span>
            </div>
            {showDefenses ? (
              <ChevronUp className="w-4 h-4 text-green-400" />
            ) : (
              <ChevronDown className="w-4 h-4 text-green-400" />
            )}
          </button>
          {showDefenses && (
            <ul className="mt-3 space-y-2">
              {dna.recommended_defenses.map((defense, idx) => (
                <li key={idx} className="flex items-start gap-2 text-sm">
                  <span className="text-green-400 font-bold">{idx + 1}.</span>
                  <span className="text-foreground/90">{defense}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Footer */}
      <div className="px-4 py-3 bg-muted/20 border-t border-border flex items-center justify-between">
        <span className="text-xs text-muted-foreground">
          Analysis Confidence: {Math.round(dna.confidence * 100)}%
        </span>
        <span className="text-xs text-muted-foreground">
          Generated {new Date(dna.generated_at).toLocaleString()}
        </span>
      </div>
    </div>
  );
}
