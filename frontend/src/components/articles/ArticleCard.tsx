import { Calendar, ExternalLink, MessageSquare } from 'lucide-react';
import type { ArticleSummary } from '../../types';

interface ArticleCardProps {
  article: ArticleSummary;
  onClick?: () => void;
  onAskAbout?: (article: ArticleSummary) => void;
}

const categoryColors: Record<string, { bg: string; text: string; border: string }> = {
  ransomware: { bg: 'bg-red-500/20', text: 'text-red-300 dark:text-red-300', border: 'border-red-500/30' },
  malware: { bg: 'bg-red-500/20', text: 'text-red-300 dark:text-red-300', border: 'border-red-500/30' },
  vulnerability: { bg: 'bg-orange-500/20', text: 'text-orange-300 dark:text-orange-300', border: 'border-orange-500/30' },
  exploit: { bg: 'bg-orange-500/20', text: 'text-orange-300 dark:text-orange-300', border: 'border-orange-500/30' },
  apt: { bg: 'bg-purple-500/20', text: 'text-purple-300 dark:text-purple-300', border: 'border-purple-500/30' },
  'threat actor': { bg: 'bg-purple-500/20', text: 'text-purple-300 dark:text-purple-300', border: 'border-purple-500/30' },
  phishing: { bg: 'bg-yellow-500/20', text: 'text-yellow-300 dark:text-yellow-300', border: 'border-yellow-500/30' },
  'data breach': { bg: 'bg-pink-500/20', text: 'text-pink-300 dark:text-pink-300', border: 'border-pink-500/30' },
  default: { bg: 'bg-primary/20', text: 'text-primary', border: 'border-primary/30' },
};

function getCategoryStyle(category: string) {
  const lower = category.toLowerCase();
  for (const [key, style] of Object.entries(categoryColors)) {
    if (lower.includes(key)) return style;
  }
  return categoryColors.default;
}

export function ArticleCard({ article, onClick, onAskAbout }: ArticleCardProps) {
  const formattedDate = new Date(article.published_at).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });

  return (
    <div
      onClick={onClick}
      className={`
        bg-card/50 border border-border rounded-lg p-4
        hover:border-primary/50 hover:bg-card
        transition-all duration-200 cursor-pointer
        ${onClick ? 'card-hover' : ''}
      `}
    >
      {/* Title */}
      <h3 className="font-semibold text-foreground mb-2 line-clamp-2">
        {article.title}
      </h3>

      {/* Summary */}
      {article.summary && (
        <p className="text-sm text-muted-foreground mb-3 line-clamp-2">
          {article.summary}
        </p>
      )}

      {article.categories && article.categories.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-3">
          {article.categories.slice(0, 3).map((category) => {
            const style = getCategoryStyle(category);
            return (
              <span
                key={category}
                className={`px-2 py-0.5 text-xs rounded-full border ${style.bg} ${style.text} ${style.border}`}
              >
                {category}
              </span>
            );
          })}
          {article.categories.length > 3 && (
            <span className="text-xs text-muted-foreground">
              +{article.categories.length - 3} more
            </span>
          )}
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <div className="flex items-center gap-1.5">
          <Calendar className="w-3.5 h-3.5" />
          {formattedDate}
        </div>
        <div className="flex items-center gap-3">
          {onAskAbout && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onAskAbout(article);
              }}
              className="flex items-center gap-1 text-primary hover:text-primary/80 transition-colors"
            >
              <MessageSquare className="w-3.5 h-3.5" />
              Ask AI
            </button>
          )}
          <a
            href={article.url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="flex items-center gap-1 text-primary hover:text-primary/80 transition-colors"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            Source
          </a>
        </div>
      </div>
    </div>
  );
}
