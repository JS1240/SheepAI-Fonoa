# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Security Intelligence Platform** - An AI-powered system that transforms cybersecurity news from The Hacker News into actionable intelligence through knowledge graphs, story evolution tracking, and predictive analytics.

### Core Vision
"Security intelligence that thinks ahead" - A conversational AI platform for security professionals that:
- Connects articles through a knowledge graph
- Tracks story evolution over time
- Predicts threat developments with confidence percentages
- Enables natural language interaction with security news

### Target Demo Moment
```
User: "Show me the latest ransomware story"

System Response:
- Timeline showing threat evolution over past month
- Knowledge graph revealing connections to recent vulnerabilities
- Prediction: "73% probability of exploit kits targeting this within 14 days"
```

## Development Status

Backend MVP is implemented with:
- RSS feed ingestion from The Hacker News
- Article processing with AI-powered entity extraction
- Knowledge graph construction
- Prediction engine with confidence scoring
- Conversational chat interface

**Next Steps**: Frontend UI and demo polish

## Project Structure

```
SheepAI-Fonoa/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── config.py            # Pydantic Settings
│   │   ├── models/              # Pydantic data models
│   │   │   ├── article.py
│   │   │   ├── graph.py
│   │   │   ├── prediction.py
│   │   │   └── conversation.py
│   │   ├── services/            # Business logic
│   │   │   ├── ingestion.py     # RSS feed parsing
│   │   │   ├── intelligence.py  # Embeddings, NLP
│   │   │   ├── graph.py         # Knowledge graph
│   │   │   ├── prediction.py    # Threat predictions
│   │   │   └── chat.py          # Conversational AI
│   │   └── api/
│   │       └── routes.py        # API endpoints
│   ├── requirements.txt
│   └── .env.example
├── docs/
│   ├── brainstorming-session-results-2025-11-29.md
│   ├── technical-architecture.md
│   └── hackathon_info.md
├── .bmad/                       # BMad Method framework (gitignored)
└── CLAUDE.md
```

## Tech Stack

### Backend
- **Python 3.11+** with FastAPI
- **Pydantic** for data validation
- **OpenAI GPT-4** for summarization, entity extraction, predictions
- **OpenAI Embeddings** for semantic similarity
- **NetworkX** for knowledge graph operations
- **feedparser** for RSS ingestion

### Frontend (Planned)
- Lovable.dev or React + Vite
- vis.js for knowledge graph visualization
- Timeline component for story evolution

## Quick Start

```bash
# Backend setup
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your OPENAI_API_KEY

# Run the server
uvicorn backend.app.main:app --reload
```

### API Endpoints

```bash
# Main chat interface (demo endpoint)
POST /api/chat
{
  "message": "Show me the latest ransomware story",
  "include_timeline": true,
  "include_graph": true,
  "include_predictions": true
}

# Trigger data ingestion
POST /api/ingest

# List articles
GET /api/articles?q=ransomware&days=7

# Get article with connections
GET /api/articles/{id}/connections
GET /api/articles/{id}/timeline
```

## BMad Method Framework

Use these slash commands for AI-assisted development workflows:

```bash
/bmad:bmm:workflows:workflow-status   # Check status
/bmad:bmm:agents:dev                  # Developer agent
/bmad:bmm:workflows:dev-story         # Implement stories
```

## Hackathon Submission

### Pitch Options
1. "Security intelligence that thinks ahead."
2. "See the threat before it sees you."
3. "Your security control tower."

### Scoring Criteria
- Creativity and Innovation (knowledge graph + predictions)
- Technical Execution (working MVP with live demo)
- Business Impact (time saved, better decisions)
- UI/UX Design (simple, professional interface)
- Demo Presentation (the ransomware query moment)

## Code Standards

- Use `ruff` for formatting (line length: 120)
- Type hints for all functions
- Pydantic models for all data validation
- Async/await for I/O operations
- Logging instead of print statements
- No emojis in code
- use the playwright mcp to test out the application