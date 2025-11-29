# Technical Architecture: Security Intelligence Platform

**Project**: Living News Intelligence Platform for The Hacker News
**Version**: MVP v1.0
**Date**: 2025-11-29

---

## System Overview

A conversational AI platform that transforms cybersecurity news into actionable intelligence through knowledge graphs, story evolution tracking, and predictive analytics.

```
+-------------------+     +----------------------+     +--------------------+
|   DATA INGESTION  | --> |  INTELLIGENCE LAYER  | --> |  PRESENTATION     |
+-------------------+     +----------------------+     +--------------------+
| - BrightData API  |     | - Article Processing |     | - Chat Interface  |
| - RSS Feed Parser |     | - Embedding Generation|     | - Timeline View   |
| - Article Storage |     | - Knowledge Graph    |     | - Graph Viz       |
+-------------------+     | - Prediction Engine  |     | - Predictions     |
                          +----------------------+     +--------------------+
```

---

## Architecture Components

### 1. Data Layer

#### 1.1 Data Sources
```python
DATA_SOURCES = {
    "primary": {
        "name": "The Hacker News",
        "rss_feed": "https://feeds.feedburner.com/TheHackersNews",
        "scraper": "BrightData",
        "frequency": "15 minutes"
    }
}
```

#### 1.2 Article Schema
```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional

class Article(BaseModel):
    id: str = Field(..., description="Unique article identifier")
    title: str
    content: str
    summary: Optional[str] = None
    url: str
    published_at: datetime
    scraped_at: datetime

    # Intelligence fields
    embedding: Optional[List[float]] = None
    entities: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    threat_actors: List[str] = Field(default_factory=list)
    vulnerabilities: List[str] = Field(default_factory=list)

    # Graph connections
    related_article_ids: List[str] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "thn-2025-001",
                "title": "Critical RCE Vulnerability in Apache...",
                "categories": ["vulnerability", "apache", "rce"]
            }
        }
```

#### 1.3 Database Design
```
PostgreSQL + pgvector

Tables:
- articles: Core article storage
- embeddings: Vector embeddings for semantic search
- entities: Extracted entities (threat actors, CVEs, products)
- connections: Graph edges between articles
- predictions: Generated predictions with confidence scores
```

---

### 2. Intelligence Layer

#### 2.1 Article Processing Pipeline
```
Raw Article
    |
    v
[1. Text Extraction] --> Clean HTML, extract main content
    |
    v
[2. Entity Extraction] --> CVEs, threat actors, products, techniques
    |
    v
[3. Summarization] --> Generate concise summary via LLM
    |
    v
[4. Embedding Generation] --> Generate vector embedding
    |
    v
[5. Connection Detection] --> Find related articles via similarity
    |
    v
[6. Graph Update] --> Add to knowledge graph
```

#### 2.2 Knowledge Graph Structure
```python
class GraphNode(BaseModel):
    id: str
    type: str  # article, entity, vulnerability, threat_actor
    properties: dict

class GraphEdge(BaseModel):
    source_id: str
    target_id: str
    relationship: str  # mentions, exploits, related_to, evolves_from
    weight: float
    timestamp: datetime
```

#### 2.3 Prediction Engine
```python
class ThreatPrediction(BaseModel):
    prediction_id: str
    article_id: str
    prediction_type: str  # exploit_likelihood, spread_forecast, patch_timeline
    description: str
    confidence: float  # 0.0 to 1.0 (displayed as percentage)
    timeframe_days: int
    reasoning: str
    generated_at: datetime

    # Example output:
    # "73% probability of exploit kits targeting this within 14 days"
```

**Prediction Methodology**:
1. Pattern matching against historical vulnerability-to-exploit timelines
2. Severity scoring (CVSS) correlation with exploitation speed
3. Threat actor activity tracking
4. Media attention as exploitation predictor

---

### 3. Interaction Layer

#### 3.1 Conversational Interface
```python
class ConversationRequest(BaseModel):
    user_id: str
    message: str
    context: Optional[List[str]] = None  # Previous message IDs

class ConversationResponse(BaseModel):
    response_text: str
    articles: List[Article] = Field(default_factory=list)
    timeline: Optional[dict] = None
    graph_data: Optional[dict] = None
    predictions: List[ThreatPrediction] = Field(default_factory=list)
```

**Supported Queries**:
- "Show me the latest ransomware story"
- "What's connected to the Apache vulnerability?"
- "How has the Log4j situation evolved?"
- "What should I watch out for this week?"

#### 3.2 Timeline Visualization Data
```python
class TimelineEvent(BaseModel):
    event_id: str
    article_id: str
    title: str
    event_type: str  # disclosure, exploit, patch, breach
    timestamp: datetime
    severity: str  # critical, high, medium, low

class StoryTimeline(BaseModel):
    story_id: str
    title: str
    events: List[TimelineEvent]
    current_status: str
    prediction: Optional[ThreatPrediction] = None
```

#### 3.3 Graph Visualization Data
```python
class GraphVisualization(BaseModel):
    nodes: List[dict]  # {id, label, type, size}
    edges: List[dict]  # {source, target, label, weight}
    focus_node: str
    depth: int = 2  # How many hops from focus
```

---

## Technology Stack

### Backend
```yaml
Language: Python 3.11+
Framework: FastAPI
Database: PostgreSQL + pgvector
Cache: Redis (optional for MVP)
Task Queue: None for MVP (sync processing)

Key Libraries:
  - pydantic: Data validation
  - httpx: Async HTTP client
  - feedparser: RSS parsing
  - beautifulsoup4: HTML parsing
  - openai: LLM API (GPT-4)
  - sentence-transformers: Embeddings (or OpenAI)
  - networkx: Graph operations
```

### Frontend
```yaml
Option A - Lovable.dev:
  - Rapid prototyping
  - AI-generated components
  - Quick iteration

Option B - React + Vite:
  - Full control
  - vis.js for graph visualization
  - react-vertical-timeline for timeline

Recommended for MVP: Lovable.dev for speed
```

### Infrastructure
```yaml
Hosting: Vercel (frontend) + Railway/Render (backend)
Database: Supabase (PostgreSQL + pgvector included)
File Storage: Not needed for MVP
Monitoring: Basic logging only for MVP
```

---

## API Design

### Core Endpoints

```yaml
POST /api/chat
  Request: { message: string, context?: string[] }
  Response: { response, articles, timeline?, graph?, predictions }

GET /api/articles
  Query: ?q=search&category=ransomware&days=7
  Response: { articles: Article[], total: int }

GET /api/articles/{id}
  Response: Article with full details

GET /api/articles/{id}/timeline
  Response: StoryTimeline

GET /api/articles/{id}/connections
  Response: GraphVisualization

GET /api/predictions
  Query: ?article_id=xxx&type=exploit
  Response: { predictions: ThreatPrediction[] }

POST /api/ingest
  Internal: Trigger data ingestion (cron or manual)
```

---

## Demo Flow Implementation

### The Core Demo Moment

**User Query**: "Show me the latest ransomware story"

**System Response Flow**:
```
1. Parse intent: topic="ransomware", action="latest"

2. Query articles:
   SELECT * FROM articles
   WHERE 'ransomware' = ANY(categories)
   ORDER BY published_at DESC LIMIT 1

3. Build timeline:
   SELECT * FROM articles
   WHERE story_id = {main_article.story_id}
   ORDER BY published_at ASC

4. Get connections:
   SELECT * FROM connections
   WHERE source_id = {article.id}
   AND relationship IN ('exploits', 'related_to')

5. Generate prediction:
   - Analyze patterns
   - Calculate confidence
   - Format: "73% probability of exploit kits targeting this within 14 days"

6. Compose response:
   - Conversational summary
   - Timeline visualization data
   - Graph visualization data
   - Prediction with confidence
```

---

## MVP Scope Definition

### In Scope (Must Have)
- [ ] RSS feed ingestion from The Hacker News
- [ ] Article storage with basic metadata
- [ ] Simple embedding-based similarity
- [ ] Chat interface with natural language
- [ ] Timeline visualization (last 30 days)
- [ ] Basic knowledge graph (2-hop connections)
- [ ] Prediction display (can be semi-hardcoded for demo)

### Out of Scope (Future)
- [ ] BrightData full scraping (RSS sufficient for demo)
- [ ] Voice interaction
- [ ] Multi-channel delivery (Telegram, etc.)
- [ ] User accounts and personalization
- [ ] Real-time updates (batch processing OK)
- [ ] Professional social proof features

---

## Development Phases

### Phase 1: Data Foundation (Day 1)
1. Set up project structure
2. Implement RSS feed parser
3. Create database schema
4. Basic article storage

### Phase 2: Intelligence (Day 1-2)
1. Embedding generation
2. Similarity detection
3. Basic knowledge graph
4. Simple prediction logic

### Phase 3: Interface (Day 2)
1. Chat endpoint
2. Frontend UI
3. Timeline component
4. Graph visualization

### Phase 4: Polish (Day 3)
1. Demo script refinement
2. Edge case handling
3. Visual polish
4. Pitch deck

---

## File Structure

```
SheepAI-Fonoa/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app
│   │   ├── config.py            # Settings
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── article.py       # Article models
│   │   │   ├── graph.py         # Graph models
│   │   │   └── prediction.py    # Prediction models
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── ingestion.py     # RSS/scraping
│   │   │   ├── intelligence.py  # Embeddings, NLP
│   │   │   ├── graph.py         # Knowledge graph
│   │   │   ├── prediction.py    # Prediction engine
│   │   │   └── chat.py          # Conversation handler
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── routes.py        # API endpoints
│   │   └── db/
│   │       ├── __init__.py
│   │       └── database.py      # DB connection
│   ├── requirements.txt
│   └── .env.example
├── frontend/                     # Lovable.dev or React
│   └── ...
├── docs/
│   ├── brainstorming-session-results-2025-11-29.md
│   └── technical-architecture.md
├── scripts/
│   └── seed_data.py             # Demo data seeding
├── CLAUDE.md
└── README.md
```

---

## Next Steps

1. **Initialize backend project** with FastAPI + dependencies
2. **Set up Supabase** with pgvector extension
3. **Implement RSS ingestion** service
4. **Build chat endpoint** with LLM integration
5. **Create frontend** via Lovable.dev
6. **Test demo flow** end-to-end
7. **Prepare pitch** and practice

---

_Architecture designed for hackathon MVP - optimize for demo impact over production scalability_
