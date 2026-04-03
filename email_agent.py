import os
import re
import json
from openai import OpenAI
from dotenv import load_dotenv
from qualifier_agent import run_qualifier
from database import save_email

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def format_name(raw_title: str) -> str:
    name_part = raw_title.split("|")[0].split("-")[0].strip()
    words = name_part.split()

    bad_words = {
        "who", "i", "in", "the", "a", "an", "unknown",
        "founder", "ceo", "vp", "head", "co-founder", "director",
        "manager", "building", "entrepreneur", "leader", "consultant",
        "linkedin", "www", "http", "https", "com",
        "helping", "growing", "leading", "driving",
        "sales", "strategy", "execution", "senior", "technology"
    }

    for word in words:
        cleaned = word.strip(".,").lower()
        if len(cleaned) > 2 and cleaned not in bad_words:
            return word.title()

    return "there"


def safe_company(company: str, link: str) -> str:
    bad_companies = {
        "in", "www", "unknown", "linkedin", "com",
        "http", "https", "co", "inc", "ltd"
    }

    if company and company.lower().strip() not in bad_companies:
        return company

    try:
        parts = link.split("/")
        slug = parts[-1]
        if slug and len(slug) > 3 and "linkedin" not in slug:
            return slug.replace("-", " ").title()
    except Exception:
        pass

    return "your company"


def clean_body(body: str, company: str) -> str:
    if re.search(r'\[.*?\]', body):
        body = re.sub(
            r"(impressed by|noticed) .*?'s.*?\[.*?\]\.",
            f"impressed by {company}'s work in the SaaS space.",
            body
        )
        body = re.sub(
            r'\[.*?\]',
            f"{company}'s work in the SaaS space",
            body
        )
    return body


def fix_subject(subject: str, company: str) -> str:
    bad_starts = [
        "boost", "boosting", "struggling", "ai tool for",
        "growing", "streamline", "improve", "enhance"
    ]
    subject_lower = subject.lower()
    if any(subject_lower.startswith(bad) for bad in bad_starts):
        return f"{company}: worth a quick chat?"
    return subject


def write_email(lead: dict, sender_name: str, sender_product: str) -> dict:
    first_name = format_name(lead["title"])
    company    = safe_company(lead["company"], lead.get("link", ""))

    prompt = f"""
You are an expert cold email copywriter. Write a short, human, personalised cold email.

Sender info:
- Name: {sender_name}
- Product: {sender_product}

Lead info:
- First name to use: {first_name}
- Company: {company}
- Role: {lead['estimated_role']}
- Why they fit: {lead['fit_reason']}

Rules:
- Address them as "{first_name}" — exact casing, no changes
- Max 3 sentences in the body. No fluff.
- First sentence must reference something real about {company} or their role
- Second sentence explains what we do in plain English — no jargon
- Third sentence is ALWAYS: "Worth a 15-min call this week?"
- NEVER use placeholder text like [specific detail], [Company], [Name] — ever
- If you don't know a specific detail, say "your work in the SaaS space"
- Do NOT use "I hope this email finds you well" or any cliche opener
- Do NOT start the subject with: "Boost", "Boosting", "Struggling", "Growing",
  "Streamline", "Improve", "Enhance", or "AI tool for"
- Each subject line must start with a completely different word
- Subject line angles to rotate between: company name first, a timeframe,
  a specific result, a role-specific question, a direct benefit statement
- Subject line must be under 8 words
- Sound like a human, not a robot
- Always start body with "Hey {{first_name}},"

Respond ONLY with valid JSON, no extra text, no markdown:
{{
  "subject": "<email subject line>",
  "body": "<full email body, use \\n for line breaks>",
  "tone_notes": "<one word: warm / direct / curious>"
}}
"""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9
    )

    raw = response.choices[0].message.content.strip()

    if raw.startswith("```"):
        raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("```").strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        result = {
            "subject": f"{company}: worth a quick chat?",
            "body": f"Hey {first_name},\n\nWe help sales teams save 10+ hours a week by automating lead generation and outreach. Worth a 15-min call this week?",
            "tone_notes": "warm"
        }

    result["body"]    = clean_body(result.get("body", ""), company)
    result["subject"] = fix_subject(result.get("subject", ""), company)

    result["first_name"]     = first_name
    result["company"]        = company
    result["estimated_role"] = lead["estimated_role"]
    result["score"]          = lead["score"]
    result["link"]           = lead["link"]
    result["title"]          = lead.get("title", "")

    return result


def run_email_agent(icp: dict, sender_name: str, sender_product: str, num_leads: int = 10) -> list[dict]:
    all_leads = run_qualifier(icp, num_leads=num_leads)
    qualified = [l for l in all_leads if l["score"] >= 60]

    print(f"\nWriting emails for {len(qualified)} qualified leads...\n")
    print("=" * 60)

    emails = []
    for i, lead in enumerate(qualified, 1):
        email = write_email(lead, sender_name, sender_product)
        emails.append(email)
        save_email(email)

        print(f"[{i}] {email['company']} — {email['estimated_role']} (score: {email['score']})")
        print(f"    Subject : {email['subject']}")
        print(f"    Tone    : {email['tone_notes']}")
        print(f"    ---")
        print(f"    {email['body']}")
        print()

    output_path = "leads_output.json"
    with open(output_path, "w") as f:
        json.dump(emails, f, indent=2)
    print(f"Saved to {output_path}")

    return emails


if __name__ == "__main__":
    icp = {
        "role": "Founder OR CEO OR VP Sales",
        "industry": "SaaS",
        "location": "India",
        "product": "AI-powered lead generation tool that automates outreach"
    }

    emails = run_email_agent(
        icp=icp,
        sender_name="Arjun",
        sender_product="an AI tool that finds qualified leads and drafts outreach automatically — saving sales teams 10+ hours a week",
        num_leads=10
    )

    print("=" * 60)
    print(f"Done. {len(emails)} emails ready to review.")