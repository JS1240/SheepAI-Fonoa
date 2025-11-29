import { useEffect, useState, useCallback } from 'react';
import {
  CommandDialog,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandShortcut,
  CommandSeparator,
} from '@/components/ui/command';
import {
  FileText,
  Search,
  Shield,
  Bug,
  Users,
  RefreshCw,
  Network,
  Download,
  Zap,
} from 'lucide-react';
import { ArticleSummary } from '@/types';

interface CommandPaletteProps {
  onSelectArticle?: (article: ArticleSummary) => void;
  onSelectCategory?: (category: string) => void;
  onAction?: (action: string) => void;
}

const THREAT_CATEGORIES = [
  { id: 'ransomware', label: 'Ransomware', icon: Shield },
  { id: 'vulnerability', label: 'Vulnerabilities', icon: Bug },
  { id: 'apt', label: 'APT Groups', icon: Users },
  { id: 'malware', label: 'Malware', icon: Zap },
];

const QUICK_ACTIONS = [
  { id: 'refresh', label: 'Refresh Feed', icon: RefreshCw, shortcut: 'R' },
  { id: 'graph', label: 'View Full Graph', icon: Network, shortcut: 'G' },
  { id: 'export', label: 'Export Report', icon: Download, shortcut: 'E' },
];

export function CommandPalette({
  onSelectArticle,
  onSelectCategory,
  onAction,
}: CommandPaletteProps) {
  const [open, setOpen] = useState(false);
  const [articles, setArticles] = useState<ArticleSummary[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((open) => !open);
      }
    };
    document.addEventListener('keydown', down);
    return () => document.removeEventListener('keydown', down);
  }, []);

  useEffect(() => {
    if (open && articles.length === 0) {
      setLoading(true);
      fetch('/api/articles?limit=10')
        .then((res) => res.json())
        .then((data) => {
          setArticles(data.articles || []);
        })
        .catch(console.error)
        .finally(() => setLoading(false));
    }
  }, [open, articles.length]);

  const handleSelectArticle = useCallback(
    (article: ArticleSummary) => {
      onSelectArticle?.(article);
      setOpen(false);
    },
    [onSelectArticle]
  );

  const handleSelectCategory = useCallback(
    (category: string) => {
      onSelectCategory?.(category);
      setOpen(false);
    },
    [onSelectCategory]
  );

  const handleAction = useCallback(
    (action: string) => {
      onAction?.(action);
      setOpen(false);
    },
    [onAction]
  );

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput placeholder="Search articles, threats, or actions..." />
      <CommandList className="bg-card border-border">
        <CommandEmpty>
          {loading ? 'Loading...' : 'No results found.'}
        </CommandEmpty>

        <CommandGroup heading="Recent Articles">
          {articles.slice(0, 5).map((article) => (
            <CommandItem
              key={article.id}
              value={article.title}
              onSelect={() => handleSelectArticle(article)}
              className="cursor-pointer hover:bg-muted"
            >
              <FileText className="mr-2 h-4 w-4 text-primary" />
              <span className="truncate flex-1">{article.title}</span>
              <span className="text-xs text-muted-foreground ml-2">
                {new Date(article.published_at).toLocaleDateString()}
              </span>
            </CommandItem>
          ))}
        </CommandGroup>

        <CommandSeparator className="bg-border" />

        <CommandGroup heading="Threat Categories">
          {THREAT_CATEGORIES.map((category) => (
            <CommandItem
              key={category.id}
              value={category.label}
              onSelect={() => handleSelectCategory(category.id)}
              className="cursor-pointer hover:bg-muted"
            >
              <category.icon className="mr-2 h-4 w-4 text-red-400" />
              <span>{category.label}</span>
            </CommandItem>
          ))}
        </CommandGroup>

        <CommandSeparator className="bg-border" />

        <CommandGroup heading="Quick Actions">
          {QUICK_ACTIONS.map((action) => (
            <CommandItem
              key={action.id}
              value={action.label}
              onSelect={() => handleAction(action.id)}
              className="cursor-pointer hover:bg-muted"
            >
              <action.icon className="mr-2 h-4 w-4 text-green-400" />
              <span>{action.label}</span>
              <CommandShortcut className="text-muted-foreground">
                {navigator.platform.includes('Mac') ? '⌘' : 'Ctrl+'}{action.shortcut}
              </CommandShortcut>
            </CommandItem>
          ))}
        </CommandGroup>
      </CommandList>

      <div className="flex items-center justify-between px-4 py-2 border-t border-border bg-card/50 text-xs text-muted-foreground">
        <div className="flex items-center gap-2">
          <Search className="h-3 w-3" />
          <span>Search</span>
        </div>
        <div className="flex items-center gap-4">
          <span>
            <kbd className="px-1.5 py-0.5 bg-muted rounded text-muted-foreground">↑↓</kbd> Navigate
          </span>
          <span>
            <kbd className="px-1.5 py-0.5 bg-muted rounded text-muted-foreground">Enter</kbd> Select
          </span>
          <span>
            <kbd className="px-1.5 py-0.5 bg-muted rounded text-muted-foreground">Esc</kbd> Close
          </span>
        </div>
      </div>
    </CommandDialog>
  );
}
