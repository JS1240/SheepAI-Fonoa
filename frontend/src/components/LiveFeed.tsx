import { useEffect, useState, useRef } from 'react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Clock, ExternalLink, Zap } from 'lucide-react';
import { ArticleSummary } from '@/types';

interface LiveFeedProps {
  onSelectArticle?: (article: ArticleSummary) => void;
}

function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

function getSeverityFromCategories(categories: string[]): 'critical' | 'high' | 'medium' | 'low' {
  const criticalKeywords = ['zero-day', 'critical', 'ransomware', 'apt'];
  const highKeywords = ['exploit', 'vulnerability', 'breach', 'malware'];
  const mediumKeywords = ['phishing', 'scam', 'fraud'];

  const lowerCategories = categories.map(c => c.toLowerCase());

  if (lowerCategories.some(c => criticalKeywords.some(k => c.includes(k)))) return 'critical';
  if (lowerCategories.some(c => highKeywords.some(k => c.includes(k)))) return 'high';
  if (lowerCategories.some(c => mediumKeywords.some(k => c.includes(k)))) return 'medium';
  return 'low';
}

function getSeverityColor(severity: string): string {
  switch (severity) {
    case 'critical': return 'bg-red-500/20 text-red-400 border-red-500/30';
    case 'high': return 'bg-orange-500/20 text-orange-400 border-orange-500/30';
    case 'medium': return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
    default: return 'bg-green-500/20 text-green-400 border-green-500/30';
  }
}

interface FeedItemProps {
  article: ArticleSummary;
  isNew?: boolean;
  onClick?: () => void;
}

function FeedItem({ article, isNew, onClick }: FeedItemProps) {
  const severity = getSeverityFromCategories(article.categories);

  return (
    <Card
      onClick={onClick}
      className={`
        p-3 mb-2 cursor-pointer transition-all duration-200
        bg-card/50 border-border/50
        hover:bg-card/80 hover:border-border
        ${isNew ? 'animate-slide-up border-l-2 border-l-primary' : ''}
      `}
    >
      <div className="flex items-start justify-between gap-2">
        <h4 className="text-sm font-medium text-foreground line-clamp-2 flex-1">
          {article.title}
        </h4>
        {isNew && (
          <Badge className="bg-primary/20 text-primary border-primary/30 text-xs shrink-0">
            <Zap className="h-3 w-3 mr-1" />
            New
          </Badge>
        )}
      </div>

      <div className="flex items-center gap-2 mt-2">
        <Badge className={`${getSeverityColor(severity)} text-xs`}>
          {severity}
        </Badge>
        {article.categories.slice(0, 2).map((cat) => (
          <Badge
            key={cat}
            variant="outline"
            className="text-xs text-muted-foreground border-border"
          >
            {cat}
          </Badge>
        ))}
      </div>

      <div className="flex items-center justify-between mt-2 text-xs text-muted-foreground">
        <span className="flex items-center gap-1">
          <Clock className="h-3 w-3" />
          {formatTimeAgo(article.published_at)}
        </span>
        <a
          href={article.url}
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="flex items-center gap-1 text-primary hover:text-primary/80 transition-colors"
        >
          <ExternalLink className="h-3 w-3" />
          Source
        </a>
      </div>
    </Card>
  );
}

function LoadingSkeleton() {
  return (
    <Card className="p-3 mb-2 bg-card/50 border-border/50">
      <Skeleton className="h-4 w-full mb-2" />
      <Skeleton className="h-4 w-3/4 mb-2" />
      <div className="flex gap-2">
        <Skeleton className="h-5 w-16" />
        <Skeleton className="h-5 w-20" />
      </div>
    </Card>
  );
}

export function LiveFeed({ onSelectArticle }: LiveFeedProps) {
  const [articles, setArticles] = useState<ArticleSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [newArticleIds, setNewArticleIds] = useState<Set<string>>(new Set());
  const previousIdsRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    async function fetchArticles() {
      try {
        const res = await fetch('/api/articles?limit=15&days=3');
        const data = await res.json();
        const newArticles: ArticleSummary[] = data.articles || [];

        const currentIds = new Set(newArticles.map(a => a.id));
        const newIds = new Set<string>();

        currentIds.forEach(id => {
          if (!previousIdsRef.current.has(id) && previousIdsRef.current.size > 0) {
            newIds.add(id);
          }
        });

        setNewArticleIds(newIds);
        previousIdsRef.current = currentIds;
        setArticles(newArticles);

        if (newIds.size > 0) {
          setTimeout(() => setNewArticleIds(new Set()), 5000);
        }
      } catch (error) {
        console.error('Failed to fetch articles:', error);
      } finally {
        setLoading(false);
      }
    }

    fetchArticles();
    const interval = setInterval(fetchArticles, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex flex-col h-full bg-background/50 rounded-lg border border-border">
      <div className="p-3 border-b border-border">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
            </span>
            Live Feed
          </h3>
          <span className="text-xs text-muted-foreground">{articles.length} articles</span>
        </div>
      </div>

      <ScrollArea className="flex-1 px-3">
        <div className="py-2">
          {loading ? (
            <>
              <LoadingSkeleton />
              <LoadingSkeleton />
              <LoadingSkeleton />
              <LoadingSkeleton />
              <LoadingSkeleton />
            </>
          ) : articles.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <p>No recent articles</p>
            </div>
          ) : (
            articles.map((article) => (
              <FeedItem
                key={article.id}
                article={article}
                isNew={newArticleIds.has(article.id)}
                onClick={() => onSelectArticle?.(article)}
              />
            ))
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
