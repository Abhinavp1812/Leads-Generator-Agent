import os
import re
import json
import requests
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

SERPER_API_KEY = os.getenv("SERPER_API_KEY")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def search_web(query: str, num_results: int = 10) -> list[dict]:
    url = "https://google.serper.dev/search"
    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {"q": query, "num": num_results}

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        leads = []
        for result in data.get("organic", []):
            leads.append({
                "title":   result.get("title", ""),
                "link":    result.get("link", ""),
                "snippet": result.get("snippet", ""),
                "source":  result.get("displayLink", "")
            })
        return leads
    except Exception as e:
        print(f"  Search failed: {e}")
        return []


def parse_natural_language_prompt(prompt: str) -> dict:
    """
    Extracts every useful detail from a rich freeform prompt.
    Handles: company name, dates, event type, location, purpose,
    lead type, budget hints, industry, and more.
    """
    system = """
You are an expert lead generation strategist.
Extract EVERY useful detail from the user's description — be thorough.
Return ONLY valid JSON with these exact fields:

{
  "goal": "<one clear sentence of what they want>",
  "company_name": "<their company name if mentioned, else null>",
  "lead_type": "<what kind of leads: events / vendors / people / companies>",
  "industry": "<industry or niche they operate in>",
  "location": "<specific location — city, area, region>",
  "role": "<target role or entity type to find>",
  "date_range": "<specific dates if mentioned, else null>",
  "purpose": "<why they want these leads: stall/exhibition/partnership/sales/etc>",
  "event_type": "<type of events if relevant: offline/trade show/wedding/corporate/etc>",
  "context": "<full context — everything useful for searching>"
}

Be specific. If they say 'Delhi NCR', keep it as 'Delhi NCR'.
If dates are mentioned, extract them exactly.
If company name is mentioned, extract it.
"""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt}
        ],
        temperature=0.1
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("```").strip()

    try:
        parsed = json.loads(raw)
        print("\nParsed prompt:")
        for k, v in parsed.items():
            if v:
                print(f"  {k}: {v}")
        return parsed
    except Exception:
        return {
            "goal":        prompt,
            "company_name": None,
            "lead_type":   "events",
            "industry":    "general",
            "location":    "India",
            "role":        "event organizer",
            "date_range":  None,
            "purpose":     "stall",
            "event_type":  "offline",
            "context":     prompt
        }


def generate_search_strategy(icp: dict) -> list[dict]:
    """
    GPT thinks like a senior researcher.
    Uses ALL parsed details — dates, company name, purpose, event type —
    to generate hyper-specific multi-source queries.
    """
    # Build a rich context string from all parsed fields
    company    = icp.get("company_name") or ""
    dates      = icp.get("date_range")   or ""
    purpose    = icp.get("purpose")      or ""
    event_type = icp.get("event_type")   or ""
    lead_type  = icp.get("lead_type")    or "leads"
    location   = icp.get("location")    or "India"
    industry   = icp.get("industry")    or ""

    date_hint = f"happening around {dates}" if dates else "upcoming 2025"
    company_hint = f"for {company}" if company else ""

    prompt = f"""
You are a senior lead generation researcher with 10 years experience.

GOAL: {icp.get('goal', '')}
COMPANY: {company or 'not specified'}
LEAD TYPE: {lead_type}
INDUSTRY: {industry}
LOCATION: {location}
PURPOSE: {purpose} {company_hint}
EVENT TYPE: {event_type}
DATE RANGE: {dates or 'upcoming'}
FULL CONTEXT: {icp.get('context', '')}
PRODUCT/OFFER: {icp.get('product', '')}

Generate 12 highly specific Google search queries to find these leads.

Rules:
1. Use the EXACT location — if Delhi NCR, use "Delhi NCR" in queries
2. Use the EXACT date range in queries where relevant — e.g. "April 2025"
3. If purpose is stall/exhibition, search for events that have stalls/exhibitions
4. Think about ALL websites where these leads exist — not just LinkedIn
5. For EVENTS leads use: JustDial, Sulekha, Eventbrite, Meetup,
   local Facebook groups, IndiaMart exhibitions, trade show sites,
   wedding expo sites, mall event pages, Times of India events,
   Delhi-specific event listing sites, Insider.in, Paytm Insider,
   bookmyshow events, college fest pages, India Expo Centre events
6. For VENDORS leads use: JustDial, IndiaMart, TradeIndia, Sulekha,
   Google Maps, local business directories
7. DO NOT use LinkedIn more than 2 times
8. Mix different sites — all 12 queries must target different sources
9. Make queries that would actually find real event organizers/vendors
   who can give a stall or space for branding

Return ONLY a valid JSON array:
[
  {{
    "query": "<specific google search query with location and dates>",
    "source_type": "<source: justdial/eventbrite/indiamart/sulekha/insider/bookmyshow/etc>",
    "priority": <1=highest relevance, 2=medium, 3=lower>
  }}
]
"""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("```").strip()

    try:
        strategy = json.loads(raw)
        print(f"\nStrategy agent generated {len(strategy)} queries:")
        for item in strategy:
            print(f"  [{item['source_type']}] {item['query'][:75]}...")
        print()
        return strategy
    except Exception as e:
        print(f"Strategy parse failed ({e}) — using fallback")
        return _fallback_strategy(icp)


def _fallback_strategy(icp: dict) -> list[dict]:
    location   = icp.get("location",    "Delhi NCR")
    industry   = icp.get("industry",    "business")
    dates      = icp.get("date_range",  "April 2025")
    event_type = icp.get("event_type",  "offline")
    company    = icp.get("company_name","")

    return [
        {"query": f'{event_type} events {location} {dates} stall booking',       "source_type": "events",      "priority": 1},
        {"query": f'site:justdial.com events exhibitions {location}',             "source_type": "justdial",    "priority": 1},
        {"query": f'site:insider.in events {location} {dates}',                   "source_type": "insider",     "priority": 1},
        {"query": f'site:bookmyshow.com events {location} April 2025',            "source_type": "bookmyshow",  "priority": 1},
        {"query": f'trade show expo exhibition {location} {dates} stall',         "source_type": "tradeshow",   "priority": 2},
        {"query": f'site:eventbrite.com {location} {dates}',                     "source_type": "eventbrite",  "priority": 2},
        {"query": f'site:meetup.com {industry} {location}',                      "source_type": "meetup",      "priority": 2},
        {"query": f'site:sulekha.com event organizer {location}',                "source_type": "sulekha",     "priority": 2},
        {"query": f'wedding bridal expo {location} {dates} vendor stall',        "source_type": "weddingexpo", "priority": 2},
        {"query": f'mall events {location} April 2025 brand activation stall',   "source_type": "mall",        "priority": 3},
        {"query": f'India Expo Centre {location} exhibition {dates}',            "source_type": "expocentre",  "priority": 3},
        {"query": f'{industry} event organizer {location} contact email {dates}', "source_type": "directory",   "priority": 3},
    ]


def search_multiple_queries(
    role: str = "",
    industry: str = "",
    location: str = "",
    total: int = 20,
    icp: dict = None
) -> list[dict]:
    if icp is None:
        icp = {
            "role": role, "industry": industry,
            "location": location, "product": "",
            "goal": f"Find {role} in {industry} in {location}",
            "lead_type": "people", "context": ""
        }

    strategy = generate_search_strategy(icp)
    strategy.sort(key=lambda x: x.get("priority", 3))

    all_leads   = []
    seen_links  = set()
    seen_titles = set()
    per_query   = max(5, total // len(strategy))

    for item in strategy:
        if len(all_leads) >= total:
            break

        query       = item["query"]
        source_type = item["source_type"]
        results     = search_web(query, num_results=per_query)

        added = 0
        for lead in results:
            link  = lead["link"]
            title = lead["title"].lower().strip()

            if link in seen_links:
                continue
            if title in seen_titles and len(title) > 10:
                continue

            seen_links.add(link)
            seen_titles.add(title)

            lead["source_type"] = source_type
            lead["priority"]    = item.get("priority", 3)
            all_leads.append(lead)
            added += 1

        print(f"  [{source_type}] +{added} leads (total: {len(all_leads)})")

    print(f"\nTotal unique leads: {len(all_leads)}")
    return all_leads[:total]


# Backward compatibility
def search_leads(query: str, num_results: int = 10) -> list[dict]:
    return search_web(query, num_results)


def build_query(role: str, industry: str, location: str) -> str:
    return f'{role} {industry} {location} contact'