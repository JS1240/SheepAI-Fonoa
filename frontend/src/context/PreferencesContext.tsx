import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import type { UserPreferences } from '../types';
import { DEFAULT_PREFERENCES } from '../types';

const STORAGE_KEY = 'security-intel-preferences';

interface PreferencesContextType {
  preferences: UserPreferences;
  updatePreferences: (updates: Partial<UserPreferences>) => void;
  resetPreferences: () => void;
  isOnboardingComplete: boolean;
  completeOnboarding: () => void;
  toggleTheme: () => void;
}

const PreferencesContext = createContext<PreferencesContextType | undefined>(undefined);

function loadPreferences(): UserPreferences {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      return { ...DEFAULT_PREFERENCES, ...JSON.parse(stored) };
    }
  } catch (error) {
    console.error('Failed to load preferences:', error);
  }
  return DEFAULT_PREFERENCES;
}

function savePreferences(preferences: UserPreferences): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences));
  } catch (error) {
    console.error('Failed to save preferences:', error);
  }
}

export function PreferencesProvider({ children }: { children: ReactNode }) {
  const [preferences, setPreferences] = useState<UserPreferences>(loadPreferences);

  useEffect(() => {
    savePreferences(preferences);
  }, [preferences]);

  // Apply theme class to document root
  useEffect(() => {
    const root = window.document.documentElement;
    if (preferences.theme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
  }, [preferences.theme]);

  const updatePreferences = (updates: Partial<UserPreferences>) => {
    setPreferences(prev => ({
      ...prev,
      ...updates,
      updatedAt: new Date().toISOString(),
    }));
  };

  const resetPreferences = () => {
    setPreferences({
      ...DEFAULT_PREFERENCES,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    });
    localStorage.removeItem(STORAGE_KEY);
  };

  const completeOnboarding = () => {
    updatePreferences({ onboardingCompleted: true });
  };

  const toggleTheme = () => {
    updatePreferences({ theme: preferences.theme === 'dark' ? 'light' : 'dark' });
  };

  return (
    <PreferencesContext.Provider
      value={{
        preferences,
        updatePreferences,
        resetPreferences,
        isOnboardingComplete: preferences.onboardingCompleted,
        completeOnboarding,
        toggleTheme,
      }}
    >
      {children}
    </PreferencesContext.Provider>
  );
}

export function usePreferences() {
  const context = useContext(PreferencesContext);
  if (!context) {
    throw new Error('usePreferences must be used within a PreferencesProvider');
  }
  return context;
}
