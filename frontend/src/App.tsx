/**
 * Main application component with routing
 */

import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import { Shield, MessageSquare, FileText, Settings, Command } from 'lucide-react';
import { HomePage } from './pages/HomePage';
import { ArticlesPage } from './pages/ArticlesPage';
import { ArticleDetailPage } from './pages/ArticleDetailPage';
import { GraphStatsCompact } from './components/common/GraphStats';
import { PreferencesProvider, usePreferences } from './context/PreferencesContext';
import OnboardingWizard from './components/OnboardingWizard';
import { CommandPalette } from './components/CommandPalette';
import { ThemeToggle } from './components/ThemeToggle';

function Header() {
  const { resetPreferences } = usePreferences();

  return (
    <header className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-6">
            {/* Logo */}
            <NavLink to="/" className="flex items-center gap-3">
              <div className="p-2 bg-primary rounded-lg glow-border">
                <Shield className="w-6 h-6 text-primary-foreground" />
              </div>
              <div>
                <h1 className="text-xl font-semibold text-foreground">Security Intelligence</h1>
                <p className="text-sm text-muted-foreground">AI-Powered Threat Analysis</p>
              </div>
            </NavLink>

            {/* Navigation */}
            <nav className="hidden md:flex items-center gap-1 ml-6">
              <NavLink
                to="/"
                end
                className={({ isActive }) =>
                  `flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-primary/20 text-primary'
                      : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                  }`
                }
              >
                <MessageSquare className="w-4 h-4" />
                Chat
              </NavLink>
              <NavLink
                to="/articles"
                className={({ isActive }) =>
                  `flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-primary/20 text-primary'
                      : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                  }`
                }
              >
                <FileText className="w-4 h-4" />
                Articles
              </NavLink>
            </nav>
          </div>

          {/* Status & Stats */}
          <div className="flex items-center gap-4">
            <GraphStatsCompact />
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              <span>Live</span>
            </div>
            <button
              onClick={() => {
                const event = new KeyboardEvent('keydown', {
                  key: 'k',
                  metaKey: true,
                  bubbles: true,
                });
                document.dispatchEvent(event);
              }}
              className="hidden sm:flex items-center gap-2 px-3 py-1.5 text-sm text-muted-foreground bg-card border border-border rounded-lg hover:bg-muted hover:text-foreground transition-colors"
              title="Open Command Palette"
            >
              <Command className="w-3.5 h-3.5" />
              <span className="text-xs">K</span>
            </button>
            <ThemeToggle />
            <button
              onClick={resetPreferences}
              className="p-2 text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition-colors"
              title="Reset Preferences"
            >
              <Settings className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}

function AppContent() {
  const { isOnboardingComplete } = usePreferences();

  if (!isOnboardingComplete) {
    return <OnboardingWizard />;
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Header />
      <main className="max-w-7xl mx-auto px-4 py-6">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/articles" element={<ArticlesPage />} />
          <Route path="/articles/:id" element={<ArticleDetailPage />} />
        </Routes>
      </main>
      <CommandPalette />
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <PreferencesProvider>
        <AppContent />
      </PreferencesProvider>
    </BrowserRouter>
  );
}

export default App;
