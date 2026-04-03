import sqlite3
from datetime import datetime

DB_PATH = "leads.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            company           TEXT,
            estimated_role    TEXT,
            score             INTEGER,
            fit_reason        TEXT,
            disqualify_reason TEXT,
            link              TEXT UNIQUE,
            status            TEXT DEFAULT 'scraped',
            created_at        TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS emails (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_link   TEXT,
            subject     TEXT,
            body        TEXT,
            tone        TEXT,
            created_at  TEXT
        )
    """)

    conn.commit()
    conn.close()


def save_lead(lead: dict):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Never re-add ignored leads
    cursor.execute("SELECT status FROM leads WHERE link = ?", (lead.get("link", ""),))
    existing = cursor.fetchone()
    if existing and existing[0] == "ignored":
        conn.close()
        return

    cursor.execute("""
        INSERT OR IGNORE INTO leads
        (company, estimated_role, score, fit_reason, disqualify_reason, link, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        lead.get("company", "Unknown"),
        lead.get("estimated_role", "Unknown"),
        lead.get("score", 0),
        lead.get("fit_reason", ""),
        lead.get("disqualify_reason", ""),
        lead.get("link", ""),
        "scraped",
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()


def save_email(email: dict):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO emails (lead_link, subject, body, tone, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        email.get("link", ""),
        email.get("subject", ""),
        email.get("body", ""),
        email.get("tone_notes", ""),
        datetime.now().isoformat()
    ))

    cursor.execute("""
        UPDATE leads SET status = 'email_drafted'
        WHERE link = ?
    """, (email.get("link", ""),))

    conn.commit()
    conn.close()


def get_all_leads() -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM leads ORDER BY score DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_ignored_leads() -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM leads WHERE status = 'ignored' ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def lead_exists(link: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM leads WHERE link = ?", (link,))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0


def delete_lead(link: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM leads WHERE link = ?", (link,))
    conn.commit()
    conn.close()


def delete_all_leads():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM leads")
    cursor.execute("DELETE FROM emails")
    conn.commit()
    conn.close()


def ignore_lead(link: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE leads SET status = 'ignored' WHERE link = ?", (link,))
    conn.commit()
    conn.close()


def restore_lead(link: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE leads SET status = 'scraped' WHERE link = ?", (link,))
    conn.commit()
    conn.close()


def get_stats() -> dict:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM leads WHERE status != 'ignored'")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM leads WHERE score >= 85 AND status != 'ignored'")
    hot = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM leads WHERE score >= 60 AND score < 85 AND status != 'ignored'")
    good = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM leads WHERE status = 'email_drafted'")
    drafted = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM leads WHERE status = 'ignored'")
    ignored = cursor.fetchone()[0]

    conn.close()
    return {
        "total":   total,
        "hot":     hot,
        "good":    good,
        "drafted": drafted,
        "ignored": ignored
    }


if __name__ == "__main__":
    init_db()

    test_lead = {
        "company": "TestCo",
        "estimated_role": "Founder & CEO",
        "score": 85,
        "fit_reason": "Exact role, exact industry",
        "disqualify_reason": None,
        "link": "https://linkedin.com/in/testco"
    }
    save_lead(test_lead)

    leads = get_all_leads()
    print(f"Leads in DB: {len(leads)}")

    stats = get_stats()
    print(f"Stats: {stats}")