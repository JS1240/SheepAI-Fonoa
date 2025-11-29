import { Clock, AlertTriangle, AlertCircle, Info } from 'lucide-react'
import type { StoryTimeline, TimelineEvent } from '../types'

interface TimelineProps {
  timeline?: StoryTimeline
}

export default function Timeline({ timeline }: TimelineProps) {
  if (!timeline) {
    return (
      <div className="p-8 text-center">
        <div className="w-16 h-16 mx-auto mb-4 bg-muted rounded-full flex items-center justify-center">
          <Clock className="w-8 h-8 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-medium text-foreground mb-2">Story Timeline</h3>
        <p className="text-muted-foreground text-sm">
          Ask about a security story to see how it evolved over time
        </p>
      </div>
    )
  }

  return (
    <div className="p-6">
      {/* Timeline Header */}
      <div className="mb-6">
        <h3 className="text-lg font-semibold text-foreground mb-1">{timeline.title}</h3>
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <span>{timeline.events.length} events</span>
          <span>
            {formatDate(timeline.first_seen)} - {formatDate(timeline.last_updated)}
          </span>
          {timeline.current_status && (
            <span className="px-2 py-0.5 rounded-full bg-primary/20 text-primary text-xs">
              {timeline.current_status}
            </span>
          )}
        </div>
      </div>

      {/* Timeline Events */}
      <div className="relative">
        {/* Vertical Line */}
        <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-gradient-to-b from-primary via-primary to-muted" />

        <div className="space-y-6">
          {timeline.events.map((event, index) => (
            <TimelineEventCard key={index} event={event} isFirst={index === 0} index={index} />
          ))}
        </div>
      </div>
    </div>
  )
}

function TimelineEventCard({ event, isFirst, index }: { event: TimelineEvent; isFirst: boolean; index: number }) {
  const severityConfig: Record<string, { color: string; icon: typeof AlertTriangle; border: string; glow: string }> = {
    high: {
      color: 'bg-red-500',
      icon: AlertTriangle,
      border: 'border-red-500/30',
      glow: 'shadow-red-500/20',
    },
    medium: {
      color: 'bg-yellow-500',
      icon: AlertCircle,
      border: 'border-yellow-500/30',
      glow: 'shadow-yellow-500/20',
    },
    low: {
      color: 'bg-green-500',
      icon: Info,
      border: 'border-green-500/30',
      glow: 'shadow-green-500/20',
    },
  }

  const config = severityConfig[event.severity] || severityConfig.medium
  const Icon = config.icon

  return (
    <div
      className="relative pl-10 animate-slide-up"
      style={{ animationDelay: `${index * 100}ms`, opacity: 0 }}
    >
      <div
        className={`absolute left-2 w-5 h-5 rounded-full ${config.color} flex items-center justify-center transition-transform duration-300 ${
          isFirst ? 'ring-4 ring-primary/30 animate-pulse scale-110' : ''
        }`}
      >
        <div className="w-2 h-2 bg-white rounded-full" />
      </div>

      <div
        className={`bg-muted/50 rounded-lg border ${config.border} p-4 card-hover ${
          isFirst ? `shadow-lg ${config.glow}` : ''
        }`}
      >
        <div className="flex items-start justify-between gap-3 mb-2">
          <div className="flex items-center gap-2">
            <Icon className={`w-4 h-4 ${getSeverityColor(event.severity)}`} />
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              {event.event_type}
            </span>
          </div>
          <span className="text-xs text-muted-foreground">{formatDate(event.timestamp)}</span>
        </div>

        <h4 className="font-medium text-foreground mb-2">{event.title}</h4>
        {event.description && (
          <p className="text-sm text-foreground/80 leading-relaxed">{event.description}</p>
        )}

        {/* Severity Badge */}
        <div className="mt-3 flex items-center gap-2">
          <span
            className={`text-xs px-2 py-0.5 rounded-full ${getSeverityBadge(event.severity)}`}
          >
            {(event.severity || 'medium').toUpperCase()} SEVERITY
          </span>
        </div>
      </div>
    </div>
  )
}

function formatDate(dateStr: string): string {
  try {
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    })
  } catch {
    return dateStr
  }
}

function getSeverityColor(severity: string): string {
  switch (severity) {
    case 'high':
      return 'text-red-400'
    case 'medium':
      return 'text-yellow-400'
    case 'low':
      return 'text-green-400'
    default:
      return 'text-muted-foreground'
  }
}

function getSeverityBadge(severity: string): string {
  switch (severity) {
    case 'high':
      return 'bg-red-500/20 text-red-300'
    case 'medium':
      return 'bg-yellow-500/20 text-yellow-300'
    case 'low':
      return 'bg-green-500/20 text-green-300'
    default:
      return 'bg-muted/20 text-foreground/80'
  }
}
