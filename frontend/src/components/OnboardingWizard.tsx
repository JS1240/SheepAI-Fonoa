import { useState } from 'react';
import { Shield, ChevronRight, ChevronLeft, Check, User, Target, Settings } from 'lucide-react';
import { usePreferences } from '../context/PreferencesContext';
import type { UserPreferences } from '../types';

const ROLES = [
  'Security Analyst',
  'Security Engineer',
  'CISO / Security Manager',
  'DevOps / SRE',
  'Software Engineer',
  'IT Administrator',
  'Threat Researcher',
  'Compliance Officer',
  'Other',
];

const INDUSTRIES = [
  'Technology / SaaS',
  'Financial Services',
  'Healthcare',
  'Government',
  'Retail / E-commerce',
  'Manufacturing',
  'Energy / Utilities',
  'Education',
  'Consulting',
  'Other',
];

const SENIORITY_LEVELS = [
  'Entry Level',
  'Mid-Level',
  'Senior',
  'Lead / Principal',
  'Manager',
  'Director',
  'Executive / C-Level',
];

const SECURITY_INTERESTS = [
  { id: 'ransomware', label: 'Ransomware', color: 'bg-red-500/20 border-red-500/50 text-red-300' },
  { id: 'vulnerabilities', label: 'Vulnerabilities', color: 'bg-orange-500/20 border-orange-500/50 text-orange-300' },
  { id: 'apt_groups', label: 'APT Groups', color: 'bg-purple-500/20 border-purple-500/50 text-purple-300' },
  { id: 'data_breaches', label: 'Data Breaches', color: 'bg-pink-500/20 border-pink-500/50 text-pink-300' },
  { id: 'cloud_security', label: 'Cloud Security', color: 'bg-cyan-500/20 border-cyan-500/50 text-cyan-300' },
  { id: 'zero_day', label: 'Zero-Day Exploits', color: 'bg-yellow-500/20 border-yellow-500/50 text-yellow-300' },
  { id: 'malware', label: 'Malware Analysis', color: 'bg-green-500/20 border-green-500/50 text-green-300' },
  { id: 'phishing', label: 'Phishing & Social Engineering', color: 'bg-blue-500/20 border-blue-500/50 text-blue-300' },
  { id: 'compliance', label: 'Compliance & Regulations', color: 'bg-slate-500/20 border-slate-500/50 text-slate-300' },
  { id: 'supply_chain', label: 'Supply Chain Attacks', color: 'bg-amber-500/20 border-amber-500/50 text-amber-300' },
];

const SUMMARY_STYLES = [
  {
    id: 'non-technical',
    title: 'Non-technical Summary',
    description: 'High-level overview perfect for quick briefings and executive communication',
    icon: User,
  },
  {
    id: 'technical',
    title: 'Technical Analysis',
    description: 'Detailed technical breakdown with CVEs, IOCs, and attack vectors',
    icon: Settings,
  },
  {
    id: 'executive',
    title: 'Executive Risk Brief',
    description: 'Business impact focus with risk assessments and strategic recommendations',
    icon: Target,
  },
];

const DETAIL_LEVELS = [
  { id: 'brief', label: 'Brief', description: 'Quick summaries, key points only' },
  { id: 'detailed', label: 'Detailed', description: 'Comprehensive analysis with context' },
  { id: 'comprehensive', label: 'Comprehensive', description: 'Full deep-dive with all available data' },
];

interface StepProps {
  preferences: UserPreferences;
  updateField: (field: keyof UserPreferences, value: unknown) => void;
}

function StepIndicator({ currentStep, totalSteps }: { currentStep: number; totalSteps: number }) {
  return (
    <div className="mb-8">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-muted-foreground">Step {currentStep} of {totalSteps}</span>
      </div>
      <div className="h-1 bg-muted rounded-full overflow-hidden">
        <div
          className="h-full bg-primary transition-all duration-300"
          style={{ width: `${(currentStep / totalSteps) * 100}%` }}
        />
      </div>
    </div>
  );
}

function ProfileStep({ preferences, updateField }: StepProps) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-foreground mb-2">Tell us about yourself</h2>
        <p className="text-muted-foreground">
          Personalize your Security Intelligence experience by sharing your professional background.
        </p>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-foreground/80 mb-2">
            What is your role?
          </label>
          <select
            value={preferences.role}
            onChange={(e) => updateField('role', e.target.value)}
            className="w-full bg-muted border border-border rounded-lg px-4 py-3 text-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
          >
            <option value="">Select your role</option>
            {ROLES.map(role => (
              <option key={role} value={role}>{role}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-foreground/80 mb-2">
            What industry are you in?
          </label>
          <select
            value={preferences.industry}
            onChange={(e) => updateField('industry', e.target.value)}
            className="w-full bg-muted border border-border rounded-lg px-4 py-3 text-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
          >
            <option value="">Select your industry</option>
            {INDUSTRIES.map(industry => (
              <option key={industry} value={industry}>{industry}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-foreground/80 mb-2">
            What is your seniority level?
          </label>
          <select
            value={preferences.seniority}
            onChange={(e) => updateField('seniority', e.target.value)}
            className="w-full bg-muted border border-border rounded-lg px-4 py-3 text-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
          >
            <option value="">Select your level</option>
            {SENIORITY_LEVELS.map(level => (
              <option key={level} value={level}>{level}</option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
}

function InterestsStep({ preferences, updateField }: StepProps) {
  const toggleInterest = (interestId: string) => {
    const current = preferences.interests || [];
    const updated = current.includes(interestId)
      ? current.filter(i => i !== interestId)
      : [...current, interestId];
    updateField('interests', updated);
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-foreground mb-2">What are you interested in?</h2>
        <p className="text-muted-foreground">
          Select topics to personalize your threat intelligence feed and get relevant alerts.
        </p>
      </div>

      <div className="flex flex-wrap gap-3">
        {SECURITY_INTERESTS.map(interest => {
          const isSelected = preferences.interests?.includes(interest.id);
          return (
            <button
              key={interest.id}
              onClick={() => toggleInterest(interest.id)}
              className={`px-4 py-2 rounded-lg border transition-all ${
                isSelected
                  ? `${interest.color} border-2`
                  : 'bg-muted/50 border-border text-muted-foreground hover:bg-muted'
              }`}
            >
              {isSelected && <Check className="w-4 h-4 inline mr-2" />}
              {interest.label}
            </button>
          );
        })}
      </div>

      {preferences.interests?.length === 0 && (
        <p className="text-sm text-muted-foreground">
          Select at least one topic to continue
        </p>
      )}
    </div>
  );
}

function PreferencesStep({ preferences, updateField }: StepProps) {
  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-foreground mb-2">Customize Your Experience</h2>
        <p className="text-muted-foreground">
          Choose how you want threat intelligence to be presented to you.
        </p>
      </div>

      {/* Summary Style */}
      <div>
        <h3 className="text-lg font-semibold text-foreground mb-4">1. Summary Style</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {SUMMARY_STYLES.map(style => {
            const isSelected = preferences.summaryStyle === style.id;
            const Icon = style.icon;
            return (
              <button
                key={style.id}
                onClick={() => updateField('summaryStyle', style.id)}
                className={`p-4 rounded-lg border text-left transition-all ${
                  isSelected
                    ? 'bg-primary/20 border-primary ring-2 ring-primary/30'
                    : 'bg-muted/50 border-border hover:bg-muted'
                }`}
              >
                <div className="flex items-start justify-between mb-3">
                  <Icon className={`w-6 h-6 ${isSelected ? 'text-primary' : 'text-muted-foreground'}`} />
                  {isSelected && (
                    <div className="w-3 h-3 bg-primary rounded-full" />
                  )}
                </div>
                <h4 className="font-medium text-foreground mb-1">{style.title}</h4>
                <p className="text-sm text-muted-foreground">{style.description}</p>
              </button>
            );
          })}
        </div>
      </div>

      {/* Detail Level */}
      <div>
        <h3 className="text-lg font-semibold text-foreground mb-4">2. Detail Level</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {DETAIL_LEVELS.map(level => {
            const isSelected = preferences.detailLevel === level.id;
            return (
              <button
                key={level.id}
                onClick={() => updateField('detailLevel', level.id)}
                className={`p-4 rounded-lg border text-left transition-all ${
                  isSelected
                    ? 'bg-primary/20 border-primary ring-2 ring-primary/30'
                    : 'bg-muted/50 border-border hover:bg-muted'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-medium text-foreground">{level.label}</h4>
                  {isSelected && (
                    <div className="w-3 h-3 bg-primary rounded-full" />
                  )}
                </div>
                <p className="text-sm text-muted-foreground">{level.description}</p>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export default function OnboardingWizard() {
  const { preferences, updatePreferences, completeOnboarding } = usePreferences();
  const [currentStep, setCurrentStep] = useState(1);
  const totalSteps = 3;

  const updateField = (field: keyof UserPreferences, value: unknown) => {
    updatePreferences({ [field]: value });
  };

  const canProceed = () => {
    switch (currentStep) {
      case 1:
        return preferences.role && preferences.industry && preferences.seniority;
      case 2:
        return preferences.interests && preferences.interests.length > 0;
      case 3:
        return true;
      default:
        return false;
    }
  };

  const handleNext = () => {
    if (currentStep < totalSteps) {
      setCurrentStep(prev => prev + 1);
    } else {
      completeOnboarding();
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(prev => prev - 1);
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-2xl">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-3 mb-4">
            <div className="p-3 bg-primary rounded-xl">
              <Shield className="w-8 h-8 text-primary-foreground" />
            </div>
          </div>
          <h1 className="text-xl font-semibold text-foreground">Security Intelligence Platform</h1>
        </div>

        {/* Card */}
        <div className="bg-card rounded-2xl border border-border p-8">
          <StepIndicator currentStep={currentStep} totalSteps={totalSteps} />

          {/* Step Content */}
          <div className="min-h-[400px]">
            {currentStep === 1 && (
              <ProfileStep preferences={preferences} updateField={updateField} />
            )}
            {currentStep === 2 && (
              <InterestsStep preferences={preferences} updateField={updateField} />
            )}
            {currentStep === 3 && (
              <PreferencesStep preferences={preferences} updateField={updateField} />
            )}
          </div>

          {/* Navigation */}
          <div className="flex items-center justify-between mt-8 pt-6 border-t border-border">
            <button
              onClick={handleBack}
              disabled={currentStep === 1}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                currentStep === 1
                  ? 'text-muted cursor-not-allowed'
                  : 'text-muted-foreground hover:text-foreground hover:bg-muted'
              }`}
            >
              <ChevronLeft className="w-4 h-4" />
              Back
            </button>

            <button
              onClick={handleNext}
              disabled={!canProceed()}
              className={`flex items-center gap-2 px-6 py-2 rounded-lg font-medium transition-all ${
                canProceed()
                  ? 'bg-primary text-primary-foreground hover:bg-primary/80'
                  : 'bg-muted text-muted-foreground cursor-not-allowed'
              }`}
            >
              {currentStep === totalSteps ? 'Finish Setup' : 'Next'}
              {currentStep < totalSteps && <ChevronRight className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
