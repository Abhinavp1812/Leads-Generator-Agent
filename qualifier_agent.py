import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from scraper_agent import search_multiple_queries
from database import init_db, save_lead

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def qualify_lead(lead: dict, icp: dict) -> dict:
    source_type = lead.get("source_type", "unknown")

    # Build rich context from all parsed fields
    company    = icp.get("company_name") or "our company"
    dates      = icp.get("date_range")   or "upcoming"
    purpose    = icp.get("purpose")      or "outreach"
    event_type = icp.get("event_type")   or ""
    location   = icp.get("location")    or ""

    prompt = f"""
You are a strict lead qualification expert.

GOAL: {icp.get('goal', '')}
COMPANY LOOKING FOR LEADS: {company}
LEAD TYPE WANTED: {icp.get('lead_type', 'leads')}
LOCATION: {location}
DATE RANGE: {dates}
PURPOSE: {purpose}
EVENT TYPE: {event_type}
PRODUCT/OFFER: {icp.get('product', '')}

Lead to evaluate:
- Title: {lead['title']}
- Snippet: {lead['snippet']}
- Source type: {source_type}
- Link: {lead['link']}

Scoring rules (be strict — most leads don't qualify):
- 85-100: PERFECT match. Exactly what was asked for.
  e.g. if looking for Delhi events in April — this is a Delhi event in April
- 60-84: GOOD match. Right type but missing one detail (wrong date, adjacent location)
- 30-59: WEAK match. Tangentially related but not directly useful
- 0-29: IRRELEVANT. Wrong location, wrong type, or no contact possible

Key disqualifiers:
- Wrong city/location entirely = max 20
- Event already passed = max 15
- No way to contact or get a stall = max 30
- Completely different industry or purpose = max 20

For each lead, also extract:
- The specific event/vendor/company name
- Whether it seems like a stall/exhibition opportunity exists
- Contact possibility (website, phone, email visible)

Respond ONLY with valid JSON:
{{
  "score": <0-100>,
  "fit_reason": "<one sentence — be specific about WHY it fits>",
  "disqualify_reason": "<one sentence weakness, or null if 85+>",
  "estimated_role": "<event organizer / vendor / exhibition / etc>",
  "company": "<event/company/org name>"
}}
"""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    usage    = response.usage
    cost_inr = ((usage.prompt_tokens / 1000) * 0.0005 +
                (usage.completion_tokens / 1000) * 0.0015) * 83

    raw = response.choices[0].message.content.strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        result = {
            "score": 0,
            "fit_reason": "Could not parse",
            "disqualify_reason": raw,
            "estimated_role": "Unknown",
            "company": "Unknown"
        }

    result["title"]       = lead["title"]
    result["link"]        = lead["link"]
    result["source_type"] = source_type
    result["cost_inr"]    = round(cost_inr, 4)
    return result


def run_qualifier(icp: dict, num_leads: int = 10) -> list[dict]:
    print(f"\nSearching {num_leads} leads across multiple sources...")
    print(f"Goal: {icp.get('goal', '')}")
    if icp.get("date_range"):
        print(f"Dates: {icp.get('date_range')}")
    if icp.get("company_name"):
        print(f"Company: {icp.get('company_name')}")
    print()

    init_db()

    raw_leads = search_multiple_queries(
        role=icp.get("role", ""),
        industry=icp.get("industry", ""),
        location=icp.get("location", ""),
        total=num_leads,
        icp=icp
    )

    print(f"Qualifying {len(raw_leads)} leads...\n")

    qualified  = []
    total_cost = 0.0

    for i, lead in enumerate(raw_leads, 1):
        result = qualify_lead(lead, icp)
        qualified.append(result)
        save_lead(result)
        total_cost += result.get("cost_inr", 0)

        status = "HOT" if result["score"] >= 85 else "GOOD" if result["score"] >= 60 else "SKIP"
        src    = result.get("source_type", "?")
        print(f"[{i:02d}] {status} ({result['score']}/100) [{src}] — {result['company']}")
        print(f"      {result['fit_reason']}")
        print()

    print(f"Total cost: ₹{round(total_cost, 4)}")
    qualified.sort(key=lambda x: x["score"], reverse=True)
    return qualified