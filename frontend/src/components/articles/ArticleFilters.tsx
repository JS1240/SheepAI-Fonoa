/**
 * Article filters component with search, category, and time range
 */

import { Search, Filter, Calendar } from 'lucide-react';

interface ArticleFiltersProps {
  query: string;
  onQueryChange: (query: string) => void;
  category: string;
  onCategoryChange: (category: string) => void;
  days: number;
  onDaysChange: (days: number) => void;
}

const CATEGORIES = [
  { value: '', label: 'All Categories' },
  { value: 'vulnerability', label: 'Vulnerabilities' },
  { value: 'malware', label: 'Malware' },
  { value: 'ransomware', label: 'Ransomware' },
  { value: 'data breach', label: 'Data Breaches' },
  { value: 'apt', label: 'APT / State-Sponsored' },
  { value: 'phishing', label: 'Phishing' },
  { value: 'zero-day', label: 'Zero-Day' },
];

const TIME_RANGES = [
  { value: 7, label: 'Last 7 days' },
  { value: 14, label: 'Last 14 days' },
  { value: 30, label: 'Last 30 days' },
  { value: 60, label: 'Last 60 days' },
  { value: 90, label: 'Last 90 days' },
];

export function ArticleFilters({
  query,
  onQueryChange,
  category,
  onCategoryChange,
  days,
  onDaysChange,
}: ArticleFiltersProps) {
  return (
    <div className="flex flex-col sm:flex-row gap-3">
      {/* Search Input */}
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <input
          type="text"
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          placeholder="Search articles..."
          className="w-full pl-10 pr-4 py-2 bg-card border border-border rounded-lg text-foreground placeholder-muted-foreground focus:outline-none focus:border-primary transition-colors"
        />
      </div>

      {/* Category Filter */}
      <div className="relative">
        <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
        <select
          value={category}
          onChange={(e) => onCategoryChange(e.target.value)}
          className="pl-10 pr-8 py-2 bg-card border border-border rounded-lg text-foreground appearance-none cursor-pointer focus:outline-none focus:border-primary transition-colors min-w-[160px]"
        >
          {CATEGORIES.map((cat) => (
            <option key={cat.value} value={cat.value}>
              {cat.label}
            </option>
          ))}
        </select>
        <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">
          <svg className="w-4 h-4 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </div>

      {/* Time Range Filter */}
      <div className="relative">
        <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
        <select
          value={days}
          onChange={(e) => onDaysChange(Number(e.target.value))}
          className="pl-10 pr-8 py-2 bg-card border border-border rounded-lg text-foreground appearance-none cursor-pointer focus:outline-none focus:border-primary transition-colors min-w-[140px]"
        >
          {TIME_RANGES.map((range) => (
            <option key={range.value} value={range.value}>
              {range.label}
            </option>
          ))}
        </select>
        <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">
          <svg className="w-4 h-4 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </div>
    </div>
  );
}
