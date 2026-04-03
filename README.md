# LeadFlow — Autonomous Lead Intelligence

An AI agent that finds leads across the entire web, scores them against your ICP, writes personalised outreach emails, and drafts them to Gmail — automatically.

Describe what you want in plain English. The agent figures out where to search.

---

## What it does

**1. Understands your goal**
Type a natural language prompt like:
> "We have a Salon Booking App. We want leads of events and vendors in Delhi NCR where we can put our stall for Style Lounge. Offline events from 14th April to 30th April."

The agent extracts company name, location, dates, purpose, and lead type automatically.

**2. Builds a multi-source search strategy**
GPT thinks like a senior researcher and decides which websites to search based on your goal — JustDial, Eventbrite, IndiaMart, Sulekha, LinkedIn, YourStory, Inc42, trade show sites, and more. Not just LinkedIn.

**3. Qualifies every lead**
Each lead is scored 0–100 against your ICP using strict GPT scoring rules. Wrong location, wrong role, or no contact signal — it gets skipped. Only real matches make it through.

**4. Writes personalised emails**
For every qualified lead, the agent writes a 3-sentence personalised cold email with a specific subject line, company reference, and soft CTA.

**5. Drafts to Gmail (optional)**
Connect your Gmail account via OAuth inside the app. HOT leads (85+) get automatically drafted to your Gmail inbox, ready to review and send.

---

## Tech stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| AI | OpenAI GPT-3.5-turbo |
| Search | Serper API (Google Search) |
| Email | Gmail API (OAuth2) |
| Frontend | Streamlit |
| Database | SQLite |
| Auth | Google OAuth2 PKCE |

---

## Project structure

```
lead-agent/
├── app.py                 Streamlit dashboard — main UI
├── scraper_agent.py       GPT strategy agent + multi-source web search
├── qualifier_agent.py     Lead scoring against ICP
├── email_agent.py         Personalised email writer
├── gmail_agent.py         Gmail OAuth connection + draft creation
├── database.py            SQLite persistence layer
├── requirements.txt       Python dependencies
├── .env.example           API key template
└── .gitignore             Protects secrets from being committed
```

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/Abhinavp1812/Leads-Generator-Agent.git
cd Leads-Generator-Agent
```

### 2. Create virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Add API keys

```bash
cp .env.example .env
```

Edit `.env` and add your keys:

```
OPENAI_API_KEY=your_openai_key_here
SERPER_API_KEY=your_serper_key_here
```

Get your keys here:
- OpenAI: https://platform.openai.com/api-keys
- Serper: https://serper.dev (2,500 free searches/month)

### 5. Run the app

```bash
streamlit run app.py
```

### 6. Connect Gmail (optional)

To enable automatic Gmail drafting:
1. Go to https://console.cloud.google.com
2. Create a project and enable the Gmail API
3. Create OAuth2 credentials (Desktop app type)
4. Download `credentials.json` and place it in the project folder
5. Click "Connect Gmail →" in the app — it opens the OAuth flow in your browser
6. Once connected, HOT leads are automatically drafted to your Gmail

Gmail connection is completely optional. The agent works without it.

---

## How to use

### Natural language mode
1. Select "Natural language" in the sidebar
2. Type your lead generation goal in plain English
3. Click "Parse & analyse →" to see what the AI understood
4. Adjust sender name and product description
5. Set how many leads to find (5–30)
6. Click "RUN AGENT →"

### Manual ICP mode
1. Select "Manual ICP" in the sidebar
2. Fill in Role, Industry, Location
3. Click "RUN AGENT →"

### Managing leads
- Filter by tier (HOT / GOOD / SKIP) or status (drafted / scraped)
- Search by company name
- Ignore leads — they never appear again in future runs
- Delete leads permanently
- Export all leads as JSON

---

## Key engineering decisions

**Why `temperature=0.3` for the qualifier?**
Consistency matters in scoring. The same lead should get the same score every run. Low temperature keeps GPT deterministic.

**Why `temperature=0.9` for the email writer?**
Creative variation. Each email should feel different even for similar leads. High temperature prevents repetitive patterns.

**Why SQLite over a cloud database?**
Zero setup, zero cost, runs locally. For a portfolio project and early-stage tool, SQLite handles thousands of leads with no configuration. Trivially swappable to PostgreSQL when needed.

**Why Serper over direct Google scraping?**
Rate limits, CAPTCHAs, and ToS violations. Serper is the clean, stable way to access Google Search results via API.

**Why `INSERT OR IGNORE` in the database?**
Deduplication by URL. The same lead appearing across multiple search queries only gets stored once. Ignored leads are permanently blocked from re-entry.

---

## Cost

Running the full pipeline (10 leads) costs approximately ₹0.50–₹2.00 in OpenAI API credits depending on lead count and email length. Cost per run is logged in the terminal output.

---

## Roadmap

- [ ] Real email address enrichment via Apollo/Clearbit API
- [ ] Direct email sending from the dashboard (no Gmail needed)
- [ ] Scheduled runs — agent runs daily and delivers fresh leads
- [ ] CSV export for leads table
- [ ] Multi-campaign support

---

## License

MIT — use it however you want.

---

Built by [Abhinav Prajapati](https://github.com/Abhinavp1812)
