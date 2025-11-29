# Security Intelligence Platform - Demo Script

## Hackathon Presentation (5 minutes)

### Opening Hook (30 seconds)

**[Show slide with headline]**

> "Every 39 seconds, a cyberattack happens somewhere in the world. Security teams read hundreds of articles daily, but they're REACTING to yesterday's threats. What if your security news could predict TOMORROW's attacks?"

### Problem Statement (45 seconds)

**[Show pain points]**

1. **Information Overload**: 50+ security articles published daily
2. **Missing Connections**: Threats evolve, but we read articles in isolation
3. **Reactive Posture**: By the time you read about a vulnerability, attackers are already exploiting it

> "Security teams are drowning in news while attackers are planning their next move."

### Solution Introduction (30 seconds)

**[Show the platform interface]**

> "We built a Security Intelligence Platform that doesn't just summarize news - it THINKS AHEAD."

**Three Key Innovations:**
1. **Story Evolution Tracking** - See how threats develop over time
2. **Knowledge Graph** - Discover hidden connections between threats
3. **Predictive Analytics** - Get threat forecasts with confidence scores

### Live Demo (2 minutes)

**Step 1: The Query**

> "Let me show you the magic. I'll type a simple question..."

**Type**: "Show me the latest ransomware story"

**Step 2: The Response**

> "Watch what happens. The AI doesn't just give me a summary..."

**Point out:**
- Natural language explanation of the threat
- Related articles automatically connected
- Severity assessment

**Step 3: Timeline Tab**

**[Click Timeline tab]**

> "This is story evolution. See how this ransomware campaign started as a small incident two weeks ago, escalated when new variants appeared, and now we're tracking active exploits."

**Point out:**
- Visual timeline with significance indicators
- How the story evolved through multiple articles
- Key inflection points

**Step 4: Knowledge Graph Tab**

**[Click Knowledge Graph tab]**

> "Now here's where it gets interesting. The knowledge graph shows connections that would take analysts hours to discover manually."

**Point out:**
- Articles connected to vulnerabilities
- Threat actors linked to campaigns
- CVEs associated with multiple stories

**Step 5: THE PREDICTION (Key Demo Moment)**

**[Click Predictions tab]**

> "And here's the game-changer. Look at this:"

**Point at the prediction card:**

> **"73% probability of exploit within 14 days"**

> "This is like a weather forecast for cybersecurity. Based on historical patterns, current indicators, and threat actor activity, our AI predicts what's LIKELY to happen next."

**Point out:**
- Confidence percentage prominently displayed
- Supporting evidence listed
- Timeframe for the prediction

### Technical Credibility (30 seconds)

> "How do we do this?"

- **GPT-4** for deep semantic understanding
- **Knowledge Graph** with NetworkX for relationship mapping
- **Embedding-based similarity** for story clustering
- **Real-time RSS ingestion** from The Hacker News

### Impact & Vision (45 seconds)

**[Show closing slide]**

> "Imagine a world where:"

1. **CISOs** get morning briefings with threat forecasts
2. **SOC Teams** prioritize based on predicted impact
3. **Executives** understand risk with simple percentages

> "We're not just summarizing the past - we're illuminating the future."

### Closing

> "This is Security Intelligence that thinks ahead. Thank you."

---

## Demo Talking Points

### If Asked About Accuracy

> "Our predictions are based on patterns from historical threat data. Like weather forecasting, we're providing probability-based guidance, not certainties. The confidence score reflects our model's certainty based on available evidence."

### If Asked About Data Sources

> "Currently ingesting from The Hacker News RSS feed. The architecture supports adding multiple sources including BrightData scraped content, CVE databases, and threat intelligence feeds."

### If Asked About Privacy/Security

> "All processing happens server-side. No article content is stored externally. The knowledge graph is built locally, and predictions use anonymized pattern analysis."

### If Asked About Future Features

1. **Alert System**: Notify when predictions cross threshold
2. **Team Collaboration**: Share insights across security teams
3. **API Integration**: Feed predictions into SIEM/SOAR platforms
4. **Custom Sources**: Add internal incident data for tailored predictions

---

## Technical Setup Checklist

### Before Demo

- [ ] Backend running (`python run.py` in backend/)
- [ ] Frontend running (`npm run dev` in frontend/)
- [ ] OpenAI API key configured in .env
- [ ] Browser open at http://localhost:5173
- [ ] Test query works
- [ ] Sample data ingested (`POST /api/ingest`)

### Backup Plan

If live demo fails:
1. Have screenshots ready of each view
2. Prepare pre-recorded video
3. Show API documentation at /docs
4. Explain architecture with diagrams

---

## Key Phrases to Remember

- "Weather forecast for cybersecurity"
- "Security intelligence that thinks ahead"
- "From reactive to predictive"
- "73% probability" (the memorable number)
- "Connections you'd miss in hours of reading"
- "Living news intelligence"
