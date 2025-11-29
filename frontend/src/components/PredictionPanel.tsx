import { useState, useEffect } from 'react'
import { Zap, TrendingUp, Clock, Shield, AlertTriangle } from 'lucide-react'
import type { ThreatPrediction } from '../types'

interface PredictionPanelProps {
  predictions?: ThreatPrediction[]
}

export default function PredictionPanel({ predictions }: PredictionPanelProps) {
  if (!predictions || predictions.length === 0) {
    return (
      <div className="p-8 text-center h-full flex flex-col items-center justify-center">
        <div className="w-16 h-16 mx-auto mb-4 bg-muted rounded-full flex items-center justify-center">
          <Zap className="w-8 h-8 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-medium text-foreground mb-2">Threat Predictions</h3>
        <p className="text-muted-foreground text-sm">
          AI-powered forecasts for exploit likelihood and attack patterns
        </p>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Zap className="w-5 h-5 text-yellow-400" />
        <h3 className="text-lg font-semibold text-foreground">Threat Intelligence Forecast</h3>
      </div>

      <div className="space-y-4">
        {predictions.map((prediction, index) => (
          <PredictionCard key={prediction.id} prediction={prediction} index={index} />
        ))}
      </div>

      {/* Disclaimer */}
      <div className="text-xs text-muted-foreground flex items-start gap-2 p-3 bg-muted/30 rounded-lg">
        <Shield className="w-4 h-4 flex-shrink-0 mt-0.5" />
        <span>
          Predictions are generated using AI analysis of threat patterns, historical data,
          and current indicators. Actual outcomes may vary.
        </span>
      </div>
    </div>
  )
}

function PredictionCard({ prediction, index = 0 }: { prediction: ThreatPrediction; index?: number }) {
  const demoCard = prediction.demo_card_data
  const confidence = demoCard?.raw_confidence
    ? Math.round(demoCard.raw_confidence * 100)
    : prediction.confidence_percentage

  // Use urgency from demo_card if available, otherwise calculate from confidence
  const urgency = demoCard?.urgency || (confidence >= 75 ? 'CRITICAL' : confidence >= 65 ? 'HIGH' : confidence >= 50 ? 'MODERATE' : 'LOW')

  const [displayValue, setDisplayValue] = useState(0)
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    const visibilityTimer = setTimeout(() => setIsVisible(true), index * 150)
    return () => clearTimeout(visibilityTimer)
  }, [index])

  useEffect(() => {
    if (!isVisible) return
    const duration = 1000
    const steps = 30
    const increment = confidence / steps
    let current = 0
    const timer = setInterval(() => {
      current += increment
      if (current >= confidence) {
        setDisplayValue(confidence)
        clearInterval(timer)
      } else {
        setDisplayValue(Math.round(current))
      }
    }, duration / steps)
    return () => clearInterval(timer)
  }, [confidence, isVisible])

  // Enhanced urgency-based styling
  const urgencyConfig = {
    CRITICAL: {
      color: 'from-red-500 to-rose-600',
      bg: 'bg-red-500/10',
      border: 'border-red-500/40',
      text: 'text-red-400',
      badgeBg: 'bg-red-500',
      badgeText: 'text-white',
      icon: AlertTriangle,
      glow: 'shadow-red-500/20',
    },
    HIGH: {
      color: 'from-orange-500 to-amber-500',
      bg: 'bg-orange-500/10',
      border: 'border-orange-500/30',
      text: 'text-orange-400',
      badgeBg: 'bg-orange-500',
      badgeText: 'text-white',
      icon: AlertTriangle,
      glow: 'shadow-orange-500/20',
    },
    MODERATE: {
      color: 'from-yellow-500 to-amber-400',
      bg: 'bg-yellow-500/10',
      border: 'border-yellow-500/30',
      text: 'text-yellow-400',
      badgeBg: 'bg-yellow-500',
      badgeText: 'text-black',
      icon: TrendingUp,
      glow: 'shadow-yellow-500/20',
    },
    LOW: {
      color: 'from-green-500 to-emerald-400',
      bg: 'bg-green-500/10',
      border: 'border-green-500/30',
      text: 'text-green-400',
      badgeBg: 'bg-green-500',
      badgeText: 'text-white',
      icon: Shield,
      glow: 'shadow-green-500/20',
    },
  }

  const config = urgencyConfig[urgency]

  // Use demo card headline or construct from description
  const headline = demoCard?.headline || `${confidence}% - ${prediction.description}`
  const timeframeDisplay = demoCard?.timeframe || `Expected within ${prediction.timeframe_days} days`
  const reasoning = demoCard?.reasoning || prediction.reasoning
  const evidence = demoCard?.evidence || prediction.supporting_evidence

  return (
    <div
      className={`rounded-xl border-2 ${config.border} ${config.bg} p-5 card-hover transition-all duration-500 shadow-lg ${config.glow} ${
        isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
      }`}
    >
      {/* Header with Urgency Badge and Confidence */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          {/* Urgency Badge */}
          <div className="flex items-center gap-2 mb-2">
            <span className={`px-2.5 py-1 rounded-full text-xs font-bold ${config.badgeBg} ${config.badgeText} uppercase tracking-wider`}>
              {urgency}
            </span>
            <span className="text-xs text-muted-foreground uppercase tracking-wide">
              {formatPredictionType(prediction.prediction_type)}
            </span>
          </div>

          {/* Headline */}
          <h4 className="text-lg font-semibold text-foreground leading-tight">
            {headline}
          </h4>
        </div>

        {/* Big Confidence Number */}
        <div className="text-right ml-4">
          <div className={`text-4xl font-bold bg-gradient-to-r ${config.color} bg-clip-text text-transparent animate-scale-in`}>
            {displayValue}%
          </div>
          <div className="text-xs text-muted-foreground">confidence</div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="mb-4">
        <div className="h-2 bg-muted rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full bg-gradient-to-r ${config.color} transition-all duration-1000 ease-out`}
            style={{ width: `${displayValue}%` }}
          />
        </div>
      </div>

      {/* Timeframe with Icon */}
      <div className="flex items-center gap-2 text-sm mb-4">
        <Clock className={`w-4 h-4 ${config.text}`} />
        <span className={`font-medium ${config.text}`}>{timeframeDisplay}</span>
      </div>

      {/* Reasoning Section */}
      {reasoning && (
        <div className="mb-4 p-3 bg-card/50 rounded-lg border border-border">
          <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1 flex items-center gap-1">
            <Zap className="w-3 h-3" />
            AI Analysis
          </p>
          <p className="text-sm text-foreground/80 leading-relaxed">{reasoning}</p>
        </div>
      )}

      {/* Supporting Evidence */}
      {evidence && evidence.length > 0 && (
        <div className="pt-3 border-t border-border">
          <p className="text-xs text-muted-foreground mb-2 uppercase tracking-wide">
            Supporting Evidence
          </p>
          <ul className="space-y-1.5">
            {evidence.slice(0, 3).map((item, idx) => (
              <li key={idx} className="text-sm text-foreground/80 flex items-start gap-2">
                <span className={`${config.text} mt-0.5 font-bold`}>*</span>
                {item}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

function formatPredictionType(type: string): string {
  return type
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}
