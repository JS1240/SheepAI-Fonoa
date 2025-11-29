# Security Intelligence Platform - Core Features

This document explains the five core intelligence features that transform raw security news into actionable insights.

---

## 1. Story Evolution Timeline

### What It Does
Tracks how a security threat develops over time, showing the progression from initial discovery to active exploitation. Instead of reading isolated articles, security teams see the complete narrative arc of a threat.

### How It Works
1. **Article Clustering**: When a new article is ingested, OpenAI embeddings calculate semantic similarity against existing articles
2. **Timeline Construction**: Related articles are ordered chronologically, creating a visual story progression
3. **Milestone Detection**: Key events are identified (initial report, new variants, exploit release, active attacks)
4. **Severity Tracking**: The timeline shows how threat severity escalates over time

### Example
```
Week 1: Initial vulnerability disclosed in Apache library
    |
Week 2: Security researchers publish proof-of-concept
    |
Week 3: First exploitation attempts detected in the wild
    |
NOW: Active ransomware campaigns leveraging this vulnerability
```

### Value for Security Teams
- **Context at a glance**: Understand threat history without reading dozens of articles
- **Pattern recognition**: See how long threats take to escalate
- **Prioritization**: Focus on threats showing rapid evolution

---

## 2. Knowledge Graph: Hidden Connections

### What It Does
Reveals relationships between articles, vulnerabilities, threat actors, and attack techniques that would take analysts hours to discover manually. The graph visualizes how threats interconnect across the security landscape.

### How It Works
1. **Entity Extraction**: GPT-4 extracts entities from each article:
   - CVE identifiers (e.g., CVE-2024-1234)
   - Threat actors (e.g., APT29, Lazarus Group)
   - Attack techniques (e.g., phishing, supply chain)
   - Target sectors (e.g., healthcare, finance)
   - Malware families (e.g., ransomware, RAT)

2. **Relationship Mapping**: NetworkX builds a graph connecting:
   - Articles to extracted entities
   - Entities to other entities (threat actor → technique → target)
   - Articles to related articles via shared entities

3. **Similarity Scoring**: OpenAI embeddings calculate semantic similarity between articles, adding weighted edges for conceptually related content

4. **Visualization**: vis-network renders an interactive graph where users can explore connections

### Graph Node Types
| Node Type | Color | Example |
|-----------|-------|---------|
| Article | Blue | "New Ransomware Targets Healthcare" |
| CVE | Red | CVE-2024-21412 |
| Threat Actor | Purple | APT41 |
| Technique | Orange | Supply Chain Attack |
| Sector | Green | Financial Services |

### Value for Security Teams
- **Discover hidden patterns**: See that three separate articles share the same threat actor
- **Attack surface mapping**: Understand which vulnerabilities affect your sector
- **Threat actor tracking**: Monitor how groups evolve their techniques

---

## 3. Threat Prediction

### What It Does
Generates probability-based forecasts of future threat developments, giving security teams a "weather forecast" for cybersecurity. Predictions include confidence scores and supporting evidence.

### How It Works
1. **Pattern Analysis**: The system analyzes historical data:
   - Average time from vulnerability disclosure to exploit availability
   - Threat actor behavior patterns
   - Media attention correlation with exploitation speed

2. **Factor Weighting**: Multiple indicators are combined:
   - **Historical patterns** (30%): Similar vulnerabilities and their exploitation timelines
   - **Severity scoring** (25%): CVSS correlation with exploitation speed
   - **Threat actor activity** (20%): Known groups' current activity levels
   - **Media attention** (15%): High visibility increases attacker interest
   - **Technical complexity** (10%): Ease of exploitation

3. **Confidence Calculation**: GPT-4 synthesizes factors into a probability score with uncertainty bounds

4. **Evidence Generation**: Each prediction includes supporting evidence explaining the reasoning

### Example Prediction
```
+------------------------------------------+
|                                          |
|    73%                                   |
|    PROBABILITY                           |
|                                          |
|    Exploit kits targeting this           |
|    vulnerability within 14 DAYS          |
|                                          |
+------------------------------------------+

EVIDENCE:
- Historical pattern: Similar vulns exploited in 12 days average
- Threat actor activity: Elevated chatter detected
- Media attention: High visibility increases attacker interest
```

### Value for Security Teams
- **Proactive defense**: Patch before exploits appear, not after
- **Resource allocation**: Focus on threats most likely to materialize
- **Executive communication**: Quantified risk for budget discussions

---

## 4. 48-Hour Threat Forecast

### What It Does
Provides an hour-by-hour risk progression for the next 48 hours, showing exactly when threat levels are expected to peak. This enables precise timing of defensive actions.

### How It Works
1. **Baseline Assessment**: Current threat state is analyzed for:
   - Exploit availability
   - Threat actor targeting indicators
   - Vulnerability exposure in the wild

2. **Timeline Modeling**: Risk is projected across 48 hours based on:
   - Typical exploit development cycles
   - Geographic attack patterns (time zones)
   - Historical incident timing data

3. **Milestone Prediction**: Key events are forecasted:
   - When exploit code is likely to be published
   - When initial attack campaigns are expected
   - When maximum exploitation activity occurs

4. **Action Recommendations**: Each milestone triggers specific defensive actions

### Example Forecast
```
48-HOUR THREAT FORECAST

NOW -------- 12h -------- 24h -------- 36h -------- 48h
 |           |            |            |            |
LOW        MODERATE      HIGH        PEAK         DECLINING
(25%)       (45%)        (65%)       (78%)        (55%)

PEAK RISK: Hour 36 - 78% probability

KEY MILESTONES:
- Hour 8: Exploit code likely published
- Hour 24: Initial attack campaigns expected
- Hour 36: Maximum exploitation activity

RECOMMENDED ACTIONS:
1. Patch critical systems within 8 hours
2. Enable enhanced monitoring by hour 12
3. Brief incident response team by hour 24
```

### Value for Security Teams
- **Precise timing**: Know exactly when to escalate defenses
- **Resource planning**: Schedule patching windows before peak risk
- **Shift coordination**: Ensure coverage during high-risk periods

---

## 5. Threat DNA - Learn From History

### What It Does
Matches current threats against historical incidents to surface patterns, lessons learned, and proven defensive strategies. Like genetic matching, it finds threats with similar "DNA" and shows what happened before.

### How It Works
1. **Threat Profiling**: Current threat is analyzed for:
   - Attack vector (phishing, supply chain, zero-day)
   - Target sectors
   - Threat actor TTPs (Tactics, Techniques, Procedures)
   - Vulnerability characteristics

2. **Historical Matching**: The profile is compared against a database of past incidents using:
   - Semantic similarity (OpenAI embeddings)
   - Entity overlap (shared CVEs, threat actors, techniques)
   - Attack pattern matching

3. **Match Scoring**: Each historical match receives:
   - **Similarity percentage**: How closely it matches
   - **Match strength**: STRONG (>75%), MODERATE (50-75%), WEAK (<50%)

4. **Lesson Extraction**: For each match, the system surfaces:
   - What happened in the historical incident
   - What defenses worked
   - What mistakes to avoid

### Example DNA Match
```
CURRENT THREAT: Supply Chain Attack on PyPI Packages

HISTORICAL MATCHES:
+--------------------------------------------------+
| 78% MATCH - 2023 NPM Supply Chain Attack         |
| STRONG MATCH                                      |
|                                                  |
| What Happened: 500+ packages compromised         |
| Lessons Learned:                                 |
| - Rapid patching reduced impact by 60%           |
| - Network segmentation limited lateral movement  |
| - Dependency scanning caught 80% of compromises  |
|                                                  |
| Shared Indicators: T1195, T1566, supply_chain    |
+--------------------------------------------------+

RECOMMENDED DEFENSES:
1. Enable dependency scanning immediately
2. Implement code signing verification
3. Monitor for unusual package updates
```

### Match Attributes
| Attribute | Description |
|-----------|-------------|
| Shared Threat Actors | Same groups involved in both incidents |
| Shared Vulnerabilities | Common CVEs or vulnerability types |
| Shared Techniques | MITRE ATT&CK techniques in common |
| Matching Attributes | Sector, attack vector, target type |

### Value for Security Teams
- **Learn from others' mistakes**: Apply lessons without suffering the breach
- **Proven playbooks**: Use defenses that worked before
- **Pattern recognition**: Identify recurring threat campaigns
- **Faster response**: Skip analysis phase with pre-validated strategies

---

## How Features Work Together

These five features create a comprehensive intelligence cycle:

```
                    +-------------------+
                    | New Article       |
                    | Ingested          |
                    +--------+----------+
                             |
              +--------------+--------------+
              |              |              |
              v              v              v
       +------+------+ +-----+-----+ +-----+------+
       | Timeline    | | Knowledge | | Entity     |
       | Clustering  | | Graph     | | Extraction |
       +------+------+ +-----+-----+ +-----+------+
              |              |              |
              +--------------+--------------+
                             |
                             v
                    +--------+----------+
                    | Threat Analysis   |
                    | (GPT-4)           |
                    +--------+----------+
                             |
              +--------------+--------------+
              |              |              |
              v              v              v
       +------+------+ +-----+-----+ +-----+------+
       | Threat      | | 48-Hour   | | Threat     |
       | Prediction  | | Forecast  | | DNA Match  |
       +-------------+ +-----------+ +------------+
```

**The Result**: Security teams move from reactive news reading to proactive threat intelligence with:
- Historical context (Timeline + DNA)
- Connection discovery (Knowledge Graph)
- Future visibility (Prediction + 48-Hour Forecast)

---

_Security Intelligence Platform - Team SheepAI - Fonoa Hackathon 2025_
