/**
 * Theme toggle component for switching between light and dark modes
 */

import { Sun, Moon } from 'lucide-react';
import { usePreferences } from '../context/PreferencesContext';

export function ThemeToggle() {
  const { preferences, toggleTheme } = usePreferences();
  const isDark = preferences.theme === 'dark';

  return (
    <button
      onClick={toggleTheme}
      className="p-2 rounded-lg transition-colors hover:bg-muted"
      title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
    >
      {isDark ? (
        <Sun className="w-4 h-4 text-muted-foreground hover:text-foreground transition-colors" />
      ) : (
        <Moon className="w-4 h-4 text-muted-foreground hover:text-foreground transition-colors" />
      )}
    </button>
  );
}
