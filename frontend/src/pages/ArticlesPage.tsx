/**
 * Articles browsing page with filters and article grid
 */

import { useNavigate } from 'react-router-dom';
import { FileText } from 'lucide-react';
import { useArticles } from '../hooks/useArticles';
import { ArticleCard } from '../components/articles/ArticleCard';
import type { ArticleSummary } from '../types';
import { ArticleFilters } from '../components/articles/ArticleFilters';
import { PageLoader } from '../components/common/LoadingSpinner';
import { PageError } from '../components/common/ErrorMessage';

export function ArticlesPage() {
  const navigate = useNavigate();
  const {
    data: articles,
    isLoading,
    error,
    refetch,
    query,
    setQuery,
    category,
    setCategory,
    days,
    setDays,
  } = useArticles({ initialDays: 14, limit: 50 });

  const handleArticleClick = (articleId: string) => {
    navigate(`/articles/${articleId}`);
  };

  const handleAskAbout = (article: ArticleSummary) => {
    navigate('/', { state: { askAboutArticle: article } });
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary/20 rounded-lg">
            <FileText className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-foreground">Security Articles</h1>
            <p className="text-sm text-muted-foreground">Browse and analyze threat intelligence</p>
          </div>
        </div>
        {articles && (
          <div className="text-sm text-muted-foreground">
            {articles.length} article{articles.length !== 1 ? 's' : ''} found
          </div>
        )}
      </div>

      {/* Filters */}
      <ArticleFilters
        query={query}
        onQueryChange={setQuery}
        category={category}
        onCategoryChange={setCategory}
        days={days}
        onDaysChange={setDays}
      />

      {/* Content */}
      {isLoading ? (
        <PageLoader message="Loading articles..." />
      ) : error ? (
        <PageError
          title="Failed to load articles"
          message={error.message}
          onRetry={refetch}
        />
      ) : articles && articles.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {articles.map((article) => (
            <ArticleCard
              key={article.id}
              article={article}
              onClick={() => handleArticleClick(article.id)}
              onAskAbout={handleAskAbout}
            />
          ))}
        </div>
      ) : (
        <div className="text-center py-12">
          <FileText className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="text-lg font-medium text-foreground mb-2">No articles found</h3>
          <p className="text-muted-foreground">
            Try adjusting your search filters or check back later for new content.
          </p>
        </div>
      )}
    </div>
  );
}
