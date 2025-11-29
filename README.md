# Security Intelligence Platform

AI-powered security intelligence platform that transforms cybersecurity news into actionable insights through knowledge graphs, story evolution tracking, and predictive analytics.

## Core Demo Moment

**"Show me the latest ransomware story"**

The system responds with:
- **Timeline**: How the threat evolved over days/weeks
- **Knowledge Graph**: Connected threats, actors, and vulnerabilities
- **Prediction**: "73% probability of exploit within 14 days"

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- OpenAI API key

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Run the server
python run.py
```

Backend runs at: http://localhost:8000
API docs at: http://localhost:8000/docs

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

Frontend runs at: http://localhost:5173

## API Endpoints

### Main Chat Interface
```bash
POST /api/chat
{
  "message": "Show me the latest ransomware story",
  "include_timeline": true,
  "include_graph": true,
  "include_predictions": true
}
```

### Other Endpoints
- `GET /api/health` - Health check
- `GET /api/articles` - List articles
- `GET /api/articles/{id}` - Get article details
- `GET /api/articles/{id}/timeline` - Story timeline
- `GET /api/articles/{id}/connections` - Knowledge graph
- `POST /api/ingest` - Trigger data ingestion
- `GET /api/predictions` - Get predictions
- `GET /api/graph/stats` - Graph statistics

## Architecture

```
User Query
    |
    v
[Chat Interface] -- Natural Language Processing
    |
    v
[Intelligence Service] -- Entity Extraction, Similarity
    |
    +--> [Knowledge Graph] -- NetworkX, Entity Connections
    |
    +--> [Prediction Engine] -- GPT-4 Analysis
    |
    v
[Response] -- Timeline + Graph + Predictions
```

## Tech Stack

### Backend
- FastAPI + Pydantic
- OpenAI GPT-4 (summarization, predictions)
- OpenAI Embeddings (semantic similarity)
- NetworkX (knowledge graph)
- feedparser (RSS ingestion)

### Frontend
- React 18 + TypeScript
- Tailwind CSS
- vis-network (graph visualization)
- Lucide React (icons)

## Demo Script

1. **Open the app** - Show the clean, professional interface
2. **Type**: "Show me the latest ransomware story"
3. **Watch the magic**:
   - Natural language response explaining the threat
   - Timeline showing story evolution
   - Knowledge graph with connected entities
   - Prediction with confidence percentage

4. **Follow-up queries**:
   - "What vulnerabilities are connected to this?"
   - "Who are the threat actors involved?"
   - "What should we prepare for?"

## Hackathon Pitch

**Problem**: Security teams drowning in news, missing critical connections

**Solution**: AI that thinks ahead - transforming news into predictions

**Key Differentiator**: Not just summarization - PREDICTION with confidence scores

**Demo Impact**: "73% chance of exploit in 14 days" (weather forecast for threats)

## Project Structure

```
SheepAI-Fonoa/
├── backend/
│   ├── app/
│   │   ├── api/routes.py
│   │   ├── models/
│   │   ├── services/
│   │   ├── config.py
│   │   └── main.py
│   ├── requirements.txt
│   └── run.py
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── types/
│   │   ├── App.tsx
│   │   └── main.tsx
│   └── package.json
└── docs/
    ├── technical-architecture.md
    └── brainstorming-session-results-*.md
```

## License

MIT
