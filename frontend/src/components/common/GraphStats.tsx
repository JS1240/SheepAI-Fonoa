/**
 * Graph statistics widget component
 */

import { useCallback } from 'react';
import { Network, FileText, Tag, Link2 } from 'lucide-react';
import { useApi } from '../../hooks/useApi';
import { graphApi, GraphStats as GraphStatsData } from '../../services/graph';
import { LoadingSpinner } from './LoadingSpinner';

interface StatItemProps {
  icon: React.ReactNode;
  label: string;
  value: number;
  color: string;
}

function StatItem({ icon, label, value, color }: StatItemProps) {
  return (
    <div className="flex items-center gap-3">
      <div className={`p-2 rounded-lg ${color}`}>
        {icon}
      </div>
      <div>
        <p className="text-2xl font-bold text-foreground">{value.toLocaleString()}</p>
        <p className="text-xs text-muted-foreground">{label}</p>
      </div>
    </div>
  );
}

export function GraphStats() {
  const fetcher = useCallback(() => graphApi.getStats(), []);
  const { data: stats, isLoading, error } = useApi<GraphStatsData>(fetcher, []);

  if (isLoading) {
    return (
      <div className="bg-card rounded-xl border border-border p-4">
        <div className="flex items-center justify-center h-24">
          <LoadingSpinner size="sm" />
        </div>
      </div>
    );
  }

  if (error || !stats) {
    return null; // Silently hide on error
  }

  return (
    <div className="bg-card rounded-xl border border-border p-4">
      <div className="flex items-center gap-2 mb-4">
        <Network className="w-5 h-5 text-primary" />
        <h3 className="font-semibold text-foreground">Knowledge Graph</h3>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <StatItem
          icon={<FileText className="w-4 h-4 text-primary" />}
          label="Articles"
          value={stats.article_nodes}
          color="bg-primary/20"
        />
        <StatItem
          icon={<Tag className="w-4 h-4 text-purple-400" />}
          label="Entities"
          value={stats.entity_nodes}
          color="bg-purple-600/20"
        />
        <StatItem
          icon={<Network className="w-4 h-4 text-emerald-400" />}
          label="Total Nodes"
          value={stats.total_nodes}
          color="bg-emerald-600/20"
        />
        <StatItem
          icon={<Link2 className="w-4 h-4 text-amber-400" />}
          label="Connections"
          value={stats.total_edges}
          color="bg-amber-600/20"
        />
      </div>
    </div>
  );
}

export function GraphStatsCompact() {
  const fetcher = useCallback(() => graphApi.getStats(), []);
  const { data: stats, isLoading } = useApi<GraphStatsData>(fetcher, []);

  if (isLoading) {
    return (
      <div className="flex items-center gap-4 text-sm text-muted-foreground">
        <span>Loading stats...</span>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="flex items-center gap-4 text-sm text-muted-foreground">
        <span>No data yet</span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-4 text-sm">
      <div className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground transition-colors" title="Articles indexed">
        <FileText className="w-4 h-4" />
        <span className="font-medium">{stats.article_nodes}</span>
      </div>
      <div className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground transition-colors" title="Total nodes in graph">
        <Network className="w-4 h-4" />
        <span className="font-medium">{stats.total_nodes}</span>
      </div>
      <div className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground transition-colors" title="Connections discovered">
        <Link2 className="w-4 h-4" />
        <span className="font-medium">{stats.total_edges}</span>
      </div>
    </div>
  );
}
