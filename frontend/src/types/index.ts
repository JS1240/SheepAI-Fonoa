export interface UserPreferences {
  // Profile
  role: string;
  industry: string;
  seniority: string;
  // Interests
  interests: string[];
  // Response preferences
  summaryStyle: 'non-technical' | 'technical' | 'executive';
  detailLevel: 'brief' | 'detailed' | 'comprehensive';
  // Theme preference
  theme: 'light' | 'dark';
  // Metadata
  onboardingCompleted: boolean;
  createdAt: string;
  updatedAt: string;
}

export const DEFAULT_PREFERENCES: UserPreferences = {
  role: '',
  industry: '',
  seniority: '',
  interests: [],
  summaryStyle: 'technical',
  detailLevel: 'detailed',
  theme: 'dark',
  onboardingCompleted: false,
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
};

export interface Article {
  id: string;
  title: string;
  url: string;
  content: string;
  summary: string;
  published_at: string;
  categories: string[];
  vulnerabilities: string[];
  threat_actors: string[];
  related_article_ids: string[];
}

export interface ArticleSummary {
  id: string;
  title: string;
  url: string;
  summary: string;
  published_at: string;
  categories: string[];
}

export interface TimelineEvent {
  event_id: string;
  article_id: string;
  title: string;
  event_type: string;
  timestamp: string;
  severity: 'high' | 'medium' | 'low';
  description?: string | null;
}

export interface StoryTimeline {
  story_id: string;
  title: string;
  events: TimelineEvent[];
  first_seen: string;
  last_updated: string;
  current_status?: string;
  prediction?: {
    next_likely_development: string;
    confidence: number;
    reasoning: string;
  };
}

export interface GraphNode {
  id: string;
  label: string;
  node_type: 'article' | 'vulnerability' | 'threat_actor' | 'category' | 'entity' | 'product' | 'technique';
  properties: Record<string, string>;
  size?: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  relationship: string;
  weight: number;
}

export interface GraphVisualization {
  nodes: GraphNode[];
  edges: GraphEdge[];
  statistics?: {
    node_count: number;
    edge_count: number;
    density?: number;
  };
  focus_node?: string;
  depth?: number;
  total_nodes?: number;
  total_edges?: number;
}

export interface ThreatPrediction {
  id: string;
  article_id: string;
  prediction_type: string;
  confidence: number;
  confidence_percentage: number;
  description: string;
  timeframe_days: number;
  supporting_evidence: string[];
  reasoning?: string;
  created_at: string;
  // Demo card fields (from backend computed_field)
  demo_card_data?: {
    headline: string;
    timeframe: string;
    urgency: 'CRITICAL' | 'HIGH' | 'MODERATE' | 'LOW';
    reasoning: string;
    evidence: string[];
    confidence_level: string;
    prediction_type: string;
    raw_confidence: number;
    raw_timeframe_days: number;
  };
}

export interface UserPreferencesForApi {
  role: string;
  industry: string;
  seniority: string;
  interests: string[];
  summary_style: 'non-technical' | 'technical' | 'executive';
  detail_level: 'brief' | 'detailed' | 'comprehensive';
}

export interface ConversationRequest {
  message: string;
  conversation_id?: string;
  include_timeline?: boolean;
  include_graph?: boolean;
  include_predictions?: boolean;
  user_preferences?: UserPreferencesForApi;
}

export interface ConversationResponse {
  response_text: string;
  articles: ArticleSummary[];
  timeline?: StoryTimeline;
  graph_data?: GraphVisualization;
  predictions?: ThreatPrediction[];
  suggested_followups: string[];
  query_understood: boolean;
  processing_time_ms: number;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  data?: ConversationResponse;
}

// Audience translation types (Explain It To... feature)
export type AudienceType = 'ceo' | 'board' | 'developers';

export interface ExplainToRequest {
  content: string;
  audience: AudienceType;
  article_id?: string;
  prediction_id?: string;
}

export interface ExplainToResponse {
  original_content: string;
  audience: AudienceType;
  translated_content: string;
  key_points: string[];
  recommended_actions: string[];
  risk_level: 'critical' | 'high' | 'medium' | 'low';
  business_impact?: string;
}

// 48-Hour Threat Forecast types
export interface HourlyForecastEntry {
  hour: number;
  timestamp: string;
  risk_level: number;
  risk_label: 'SAFE' | 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL';
  event_description?: string;
  contributing_factors: string[];
}

export interface ThreatForecast {
  forecast_id: string;
  article_id: string;
  threat_name: string;
  entries: HourlyForecastEntry[];
  peak_risk_hour: number;
  peak_risk_level: number;
  summary: string;
  key_milestones: string[];
  recommended_actions: string[];
  generated_at: string;
  confidence: number;
  urgency_level: 'CRITICAL' | 'HIGH' | 'MODERATE' | 'LOW';
}

// Threat DNA Matching types
export interface DNAMatch {
  match_id: string;
  historical_article_id: string;
  historical_title: string;
  historical_date: string;
  similarity_score: number;
  match_strength: 'STRONG' | 'MODERATE' | 'WEAK' | 'PARTIAL';
  matching_attributes: string[];
  shared_threat_actors: string[];
  shared_vulnerabilities: string[];
  shared_techniques: string[];
  historical_outcome: string;
  lessons_learned: string[];
}

export interface ThreatDNA {
  dna_id: string;
  article_id: string;
  threat_name: string;
  threat_type: string;
  attack_vector: string;
  target_sectors: string[];
  indicators: string[];
  techniques: string[];
  matches: DNAMatch[];
  summary: string;
  risk_assessment: string;
  recommended_defenses: string[];
  generated_at: string;
  confidence: number;
  top_match_score: number;
  has_strong_precedent: boolean;
}

// Infographic types
export type InfographicType = 'threat_summary' | 'timeline' | 'knowledge_graph';

export type InfographicStatus = 'pending' | 'generating' | 'completed' | 'failed';

export interface Infographic {
  id: string;
  article_id: string;
  infographic_type: InfographicType;
  status: InfographicStatus;
  storage_path?: string;
  public_url?: string;
  prompt_used?: string;
  generation_time_ms?: number;
  error_message?: string;
  created_at: string;
  completed_at?: string;
}

export interface InfographicResponse {
  infographic: Infographic;
  is_cached: boolean;
}

export interface ArticleInfographics {
  article_id: string;
  infographics: Record<InfographicType, string>;
}
