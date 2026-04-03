import os
import base64
import json
from email.mime.text import MIMEText
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES     = ["https://www.googleapis.com/auth/gmail.compose"]
CREDS_FILE = "credentials.json"
TOKEN_FILE  = "token.json"
DRAFTS_LOG  = "drafts_log.json"


def get_gmail_service():
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def create_draft(service, to: str, subject: str, body: str) -> dict:
    message = MIMEText(body)
    message["to"]      = to
    message["subject"] = subject

    raw   = base64.urlsafe_b64encode(message.as_bytes()).decode()
    draft = service.users().drafts().create(
        userId="me",
        body={"message": {"raw": raw}}
    ).execute()

    return draft


def load_existing_drafts() -> list[dict]:
    if os.path.exists(DRAFTS_LOG):
        with open(DRAFTS_LOG) as f:
            try:
                return json.load(f)
            except Exception:
                return []
    return []


def save_drafts_log(drafts: list[dict]):
    with open(DRAFTS_LOG, "w") as f:
        json.dump(drafts, f, indent=2)


def draft_all_emails(emails: list[dict]) -> list[dict]:
    print("Connecting to Gmail...")
    service = get_gmail_service()
    print("Connected.\n")

    # Load existing drafts — never duplicate same lead
    existing       = load_existing_drafts()
    existing_links = {d.get("lead_link", "") for d in existing}

    newly_drafted = []
    skipped       = []

    for email in emails:
        # Only auto-draft HOT leads (85+)
        # GOOD leads need manual review first
        if email["score"] < 85:
            skipped.append(email["company"])
            continue

        # Skip if this lead was already drafted
        lead_link = email.get("link", "")
        if lead_link in existing_links:
            print(f"Already drafted: {email['company']} — skipping duplicate")
            continue

        # Build a guessed email address
        # In production: enrich with Apollo or Clearbit API for real addresses
        clean_company = email['company'].lower().replace(' ', '').replace('.', '').replace(',', '')
        to_address = f"{email['first_name'].lower()}@{clean_company}.com"

        try:
            draft = create_draft(
                service=service,
                to=to_address,
                subject=email["subject"],
                body=email["body"]
            )

            entry = {
                "company":   email["company"],
                "to":        to_address,
                "subject":   email["subject"],
                "draft_id":  draft["id"],
                "lead_link": lead_link,
                "score":     email["score"]
            }
            newly_drafted.append(entry)
            existing_links.add(lead_link)
            print(f"Drafted: {email['company']} — {email['subject']}")

        except Exception as e:
            print(f"Failed for {email['company']}: {e}")

    # Merge old + new, save everything
    all_drafts = existing + newly_drafted
    save_drafts_log(all_drafts)

    print(f"\n{len(newly_drafted)} new drafts created. {len(all_drafts)} total in log.")
    if skipped:
        print(f"Skipped (GOOD tier / already drafted): {', '.join(skipped)}")

    return all_drafts


if __name__ == "__main__":
    if not os.path.exists("leads_output.json"):
        print("No leads_output.json found. Run email_agent.py first.")
        exit()

    with open("leads_output.json") as f:
        emails = json.load(f)

    print(f"Loaded {len(emails)} emails from leads_output.json")
    draft_all_emails(emails)