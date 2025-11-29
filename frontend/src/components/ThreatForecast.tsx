/**
 * 48-Hour Threat Forecast Component
 * Timeline visualization with hourly risk progression
 */

import { useState, useEffect } from 'react';
import { Clock, AlertTriangle, TrendingUp, Shield, Loader2, ChevronRight } from 'lucide-react';
import { getThreatForecast } from '../services/forecast';
import type { ThreatForecast as ThreatForecastType, HourlyForecastEntry } from '../types';

interface ThreatForecastProps {
  articleId: string;
  className?: string;
}

const RISK_COLORS = {
  SAFE: { bg: 'bg-blue-500', text: 'text-blue-400', border: 'border-blue-500/30' },
  LOW: { bg: 'bg-green-500', text: 'text-green-400', border: 'border-green-500/30' },
  MODERATE: { bg: 'bg-yellow-500', text: 'text-yellow-400', border: 'border-yellow-500/30' },
  HIGH: { bg: 'bg-orange-500', text: 'text-orange-400', border: 'border-orange-500/30' },
  CRITICAL: { bg: 'bg-red-500', text: 'text-red-400', border: 'border-red-500/30' },
};

const URGENCY_COLORS = {
  CRITICAL: { bg: 'bg-red-500/20', text: 'text-red-400', border: 'border-red-500/30' },
  HIGH: { bg: 'bg-orange-500/20', text: 'text-orange-400', border: 'border-orange-500/30' },
  MODERATE: { bg: 'bg-yellow-500/20', text: 'text-yellow-400', border: 'border-yellow-500/30' },
  LOW: { bg: 'bg-green-500/20', text: 'text-green-400', border: 'border-green-500/30' },
};

export default function ThreatForecast({ articleId, className = '' }: ThreatForecastProps) {
  const [forecast, setForecast] = useState<ThreatForecastType | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);

  useEffect(() => {
    if (articleId) {
      loadForecast();
    }
  }, [articleId]);

  const loadForecast = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getThreatForecast(articleId);
      setForecast(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load forecast');
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className={`bg-card rounded-xl border border-border p-6 ${className}`}>
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-8 h-8 text-primary animate-spin" />
          <span className="ml-3 text-muted-foreground">Generating 48-hour forecast...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`bg-card rounded-xl border border-border p-6 ${className}`}>
        <div className="text-center py-8">
          <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-3" />
          <p className="text-foreground font-medium">Failed to load forecast</p>
          <p className="text-sm text-muted-foreground mt-1">{error}</p>
          <button
            onClick={loadForecast}
            className="mt-4 px-4 py-2 text-sm bg-muted hover:bg-muted/80 rounded-lg transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  if (!forecast) {
    return null;
  }

  const urgencyColor = URGENCY_COLORS[forecast.urgency_level];

  // Get key hours for the mini timeline (every 6 hours + peak)
  const keyHours = [0, 6, 12, 18, 24, 30, 36, 42, 48];
  const keyEntries = keyHours
    .map((h) => forecast.entries.find((e) => e.hour === h))
    .filter(Boolean) as HourlyForecastEntry[];

  return (
    <div className={`bg-card rounded-xl border border-border overflow-hidden ${className}`}>
      {/* Header */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary/10 rounded-lg">
              <Clock className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h3 className="font-semibold text-foreground">48-Hour Threat Forecast</h3>
              <p className="text-sm text-muted-foreground">{forecast.threat_name}</p>
            </div>
          </div>
          <span
            className={`px-3 py-1 rounded-full text-xs font-bold uppercase ${urgencyColor.bg} ${urgencyColor.text} ${urgencyColor.border} border`}
          >
            {forecast.urgency_level}
          </span>
        </div>
      </div>

      {/* Summary */}
      <div className="p-4 bg-muted/30">
        <p className="text-sm text-foreground leading-relaxed">{forecast.summary}</p>
      </div>

      {/* Risk Timeline Visualization */}
      <div className="p-4">
        <div className="flex items-center gap-2 mb-3">
          <TrendingUp className="w-4 h-4 text-muted-foreground" />
          <span className="text-sm font-medium text-foreground">Risk Progression</span>
          <span className="text-xs text-muted-foreground ml-auto">
            Peak: Hour {forecast.peak_risk_hour} ({Math.round(forecast.peak_risk_level * 100)}%)
          </span>
        </div>

        {/* Timeline bars */}
        <div className="relative">
          <div className="flex gap-0.5 h-16 items-end">
            {forecast.entries.slice(0, 48).map((entry, idx) => {
              const color = RISK_COLORS[entry.risk_label];
              const height = Math.max(entry.risk_level * 100, 5);
              const isPeak = entry.hour === forecast.peak_risk_hour;
              return (
                <div
                  key={idx}
                  className="flex-1 relative group"
                  title={`Hour ${entry.hour}: ${entry.risk_label} (${Math.round(entry.risk_level * 100)}%)`}
                >
                  <div
                    className={`w-full rounded-t transition-all ${color.bg} ${
                      isPeak ? 'ring-2 ring-white/50' : 'opacity-80 hover:opacity-100'
                    }`}
                    style={{ height: `${height}%` }}
                  />
                  {isPeak && (
                    <div className="absolute -top-6 left-1/2 -translate-x-1/2 text-xs font-bold text-red-400">
                      PEAK
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Hour markers */}
          <div className="flex justify-between mt-2 text-xs text-muted-foreground">
            <span>Now</span>
            <span>12h</span>
            <span>24h</span>
            <span>36h</span>
            <span>48h</span>
          </div>
        </div>
      </div>

      {/* Key Milestones */}
      {forecast.key_milestones.length > 0 && (
        <div className="px-4 pb-4">
          <div className="flex items-center gap-2 mb-2">
            <Shield className="w-4 h-4 text-amber-400" />
            <span className="text-sm font-medium text-foreground">Key Milestones</span>
          </div>
          <ul className="space-y-1.5">
            {forecast.key_milestones.slice(0, isExpanded ? undefined : 3).map((milestone, idx) => (
              <li key={idx} className="flex items-start gap-2 text-sm">
                <ChevronRight className="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" />
                <span className="text-foreground/90">{milestone}</span>
              </li>
            ))}
          </ul>
          {forecast.key_milestones.length > 3 && (
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="mt-2 text-xs text-primary hover:text-primary/80"
            >
              {isExpanded ? 'Show less' : `Show ${forecast.key_milestones.length - 3} more`}
            </button>
          )}
        </div>
      )}

      {/* Recommended Actions */}
      {forecast.recommended_actions.length > 0 && (
        <div className="p-4 bg-amber-500/10 border-t border-amber-500/20">
          <p className="text-xs text-amber-400 uppercase tracking-wide mb-2 font-medium">
            Recommended Actions
          </p>
          <ul className="space-y-1.5">
            {forecast.recommended_actions.map((action, idx) => (
              <li key={idx} className="flex items-start gap-2 text-sm">
                <span className="text-amber-400 font-bold">{idx + 1}.</span>
                <span className="text-foreground/90">{action}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Footer */}
      <div className="px-4 py-3 bg-muted/20 border-t border-border flex items-center justify-between">
        <span className="text-xs text-muted-foreground">
          Confidence: {Math.round(forecast.confidence * 100)}%
        </span>
        <span className="text-xs text-muted-foreground">
          Generated {new Date(forecast.generated_at).toLocaleString()}
        </span>
      </div>
    </div>
  );
}
