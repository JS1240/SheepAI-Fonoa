/**
 * Error message component with retry button
 */

import { AlertTriangle, RefreshCw } from 'lucide-react';

interface ErrorMessageProps {
  title?: string;
  message: string;
  onRetry?: () => void;
}

export function ErrorMessage({
  title = 'Error',
  message,
  onRetry,
}: ErrorMessageProps) {
  return (
    <div className="bg-threat-critical/10 border border-threat-critical/30 rounded-lg p-4">
      <div className="flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-threat-critical flex-shrink-0 mt-0.5" />
        <div className="flex-1">
          <h4 className="font-medium text-threat-critical">{title}</h4>
          <p className="text-sm text-muted-foreground mt-1">{message}</p>
          {onRetry && (
            <button
              onClick={onRetry}
              className="mt-3 flex items-center gap-2 text-sm text-primary hover:text-primary/80 transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              Try again
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Full-page error state
 */
export function PageError({
  title = 'Something went wrong',
  message,
  onRetry,
}: ErrorMessageProps) {
  return (
    <div className="flex items-center justify-center min-h-[400px]">
      <div className="text-center max-w-md">
        <AlertTriangle className="w-12 h-12 text-threat-critical mx-auto mb-4" />
        <h2 className="text-xl font-semibold text-foreground mb-2">{title}</h2>
        <p className="text-muted-foreground mb-4">{message}</p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary/80 text-primary-foreground rounded-lg transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Retry
          </button>
        )}
      </div>
    </div>
  );
}
