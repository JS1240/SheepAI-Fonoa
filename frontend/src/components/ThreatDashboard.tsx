import { useEffect, useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { AreaChart, Area, ResponsiveContainer, Tooltip } from 'recharts';
import { FileText, Shield, AlertTriangle, Network } from 'lucide-react';

interface DashboardStats {
  totalArticles: number;
  activeThreats: number;
  highSeverityPredictions: number;
  graphEntities: number;
  articleTrend: { date: string; count: number }[];
}

interface StatCardProps {
  title: string;
  value: number;
  icon: React.ReactNode;
  trend?: number;
  color: string;
  loading?: boolean;
}

function StatCard({ title, value, icon, trend, color, loading }: StatCardProps) {
  if (loading) {
    return (
      <Card className="bg-card/50 border-border/50">
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <Skeleton className="h-8 w-8 rounded-full" />
            <Skeleton className="h-4 w-12" />
          </div>
          <Skeleton className="h-8 w-16 mt-2" />
          <Skeleton className="h-4 w-24 mt-1" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-card/50 border-border/50 hover:border-border transition-all duration-200 card-hover">
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div className={`p-2 rounded-lg ${color}`}>
            {icon}
          </div>
          {trend !== undefined && (
            <span className={`text-xs font-medium ${trend >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {trend >= 0 ? '+' : ''}{trend}%
            </span>
          )}
        </div>
        <div className="mt-3">
          <p className="text-2xl font-bold text-foreground animate-scale-in">{value.toLocaleString()}</p>
          <p className="text-sm text-muted-foreground mt-1">{title}</p>
        </div>
      </CardContent>
    </Card>
  );
}

interface TrendChartProps {
  data: { date: string; count: number }[];
  loading?: boolean;
}

function TrendChart({ data, loading }: TrendChartProps) {
  if (loading) {
    return (
      <Card className="bg-card/50 border-border/50">
        <CardContent className="p-4">
          <Skeleton className="h-4 w-32 mb-2" />
          <Skeleton className="h-24 w-full" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-card/50 border-border/50 col-span-2">
      <CardContent className="p-4">
        <p className="text-sm text-muted-foreground mb-2">Article Volume (7 days)</p>
        <div className="h-24">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data}>
              <defs>
                <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#0ca5eb" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#0ca5eb" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1e293b',
                  border: '1px solid #334155',
                  borderRadius: '8px',
                  color: '#e2e8f0'
                }}
                labelStyle={{ color: '#94a3b8' }}
              />
              <Area
                type="monotone"
                dataKey="count"
                stroke="#0ca5eb"
                fillOpacity={1}
                fill="url(#colorCount)"
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}

export function ThreatDashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchStats() {
      try {
        const [articlesRes, predictionsRes] = await Promise.all([
          fetch('/api/articles?days=7'),
          fetch('/api/predictions')
        ]);

        const articlesData = articlesRes.ok ? await articlesRes.json() : { articles: [] };
        const predictionsData = predictionsRes.ok ? await predictionsRes.json() : { predictions: [] };

        const articles = articlesData.articles || [];
        const predictions = predictionsData.predictions || [];

        const now = new Date();
        const oneDayAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000);
        const recentArticles = articles.filter((a: { published_at: string }) =>
          new Date(a.published_at) > oneDayAgo
        );

        const threatCategories = ['ransomware', 'malware', 'apt', 'vulnerability', 'exploit'];
        const activeThreats = articles.filter((a: { categories: string[] }) =>
          a.categories?.some((c: string) => threatCategories.includes(c.toLowerCase()))
        ).length;

        const highSeverity = predictions.filter((p: { confidence_percentage: number }) =>
          p.confidence_percentage >= 70
        ).length;

        const uniqueEntities = new Set<string>();
        articles.forEach((a: { threat_actors?: string[]; vulnerabilities?: string[] }) => {
          a.threat_actors?.forEach((t: string) => uniqueEntities.add(t));
          a.vulnerabilities?.forEach((v: string) => uniqueEntities.add(v));
        });

        const trendData: { date: string; count: number }[] = [];
        for (let i = 6; i >= 0; i--) {
          const date = new Date(now);
          date.setDate(date.getDate() - i);
          const dateStr = date.toISOString().split('T')[0];
          const count = articles.filter((a: { published_at: string }) =>
            a.published_at.startsWith(dateStr)
          ).length;
          trendData.push({
            date: date.toLocaleDateString('en-US', { weekday: 'short' }),
            count
          });
        }

        setStats({
          totalArticles: recentArticles.length,
          activeThreats,
          highSeverityPredictions: highSeverity,
          graphEntities: uniqueEntities.size,
          articleTrend: trendData
        });
      } catch (error) {
        console.error('Failed to fetch dashboard stats:', error);
        setStats({
          totalArticles: 0,
          activeThreats: 0,
          highSeverityPredictions: 0,
          graphEntities: 0,
          articleTrend: []
        });
      } finally {
        setLoading(false);
      }
    }

    fetchStats();
    const interval = setInterval(fetchStats, 60000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="grid grid-cols-2 lg:grid-cols-6 gap-4 mb-6 animate-fade-in">
      <StatCard
        title="Articles (24h)"
        value={stats?.totalArticles ?? 0}
        icon={<FileText className="h-4 w-4 text-blue-400" />}
        color="bg-blue-500/10"
        trend={12}
        loading={loading}
      />
      <StatCard
        title="Active Threats"
        value={stats?.activeThreats ?? 0}
        icon={<Shield className="h-4 w-4 text-red-400" />}
        color="bg-red-500/10"
        loading={loading}
      />
      <StatCard
        title="High Severity"
        value={stats?.highSeverityPredictions ?? 0}
        icon={<AlertTriangle className="h-4 w-4 text-orange-400" />}
        color="bg-orange-500/10"
        loading={loading}
      />
      <StatCard
        title="Graph Entities"
        value={stats?.graphEntities ?? 0}
        icon={<Network className="h-4 w-4 text-green-400" />}
        color="bg-green-500/10"
        loading={loading}
      />
      <TrendChart
        data={stats?.articleTrend ?? []}
        loading={loading}
      />
    </div>
  );
}
