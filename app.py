import os
import json
import streamlit as st
from dotenv import load_dotenv
from database import (
    init_db, get_all_leads, get_stats, delete_all_leads,
    delete_lead, ignore_lead, get_ignored_leads, restore_lead
)
from email_agent import run_email_agent
from gmail_agent import (
    draft_all_emails, DRAFTS_LOG,
    get_gmail_service, TOKEN_FILE, CREDS_FILE
)
from scraper_agent import parse_natural_language_prompt

load_dotenv()

st.set_page_config(
    page_title="LeadFlow",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@300;400;500&family=Outfit:wght@300;400;500&display=swap');

*, *::before, *::after { box-sizing: border-box; }
html, body, [data-testid="stAppViewContainer"] {
    background: #050508 !important; color: #e8e6e0;
    font-family: 'Outfit', sans-serif;
}
[data-testid="stHeader"] {
    background: transparent !important;
    border-bottom: 0.5px solid rgba(255,255,255,0.05);
}
#MainMenu, footer, [data-testid="stToolbar"] { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; }
h1,h2,h3 { font-family: 'Syne', sans-serif; letter-spacing: -0.02em; }
::-webkit-scrollbar { width: 3px; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 2px; }

[data-testid="metric-container"] {
    background: rgba(255,255,255,0.02) !important;
    border: 0.5px solid rgba(255,255,255,0.07) !important;
    border-radius: 12px !important; padding: 20px !important;
}
[data-testid="stMetricValue"] {
    font-family: 'Syne', sans-serif !important;
    font-size: 28px !important; font-weight: 700 !important; color: #ffffff !important;
}
[data-testid="stMetricLabel"] {
    font-family: 'IBM Plex Mono', monospace !important; font-size: 10px !important;
    letter-spacing: 0.1em !important; color: rgba(255,255,255,0.35) !important;
    text-transform: uppercase !important;
}
[data-testid="stExpander"] {
    background: rgba(255,255,255,0.02) !important;
    border: 0.5px solid rgba(255,255,255,0.07) !important;
    border-radius: 10px !important; margin-bottom: 6px !important;
}
details summary {
    font-family: 'Outfit', sans-serif !important;
    font-size: 13px !important; color: rgba(255,255,255,0.8) !important;
}
.stButton > button {
    font-family: 'IBM Plex Mono', monospace !important; font-size: 11px !important;
    letter-spacing: 0.08em !important; border-radius: 6px !important;
    border: 0.5px solid rgba(255,255,255,0.12) !important;
    background: transparent !important; color: rgba(255,255,255,0.7) !important;
    text-transform: uppercase !important; transition: all 0.2s !important;
}
.stButton > button:hover {
    background: rgba(255,255,255,0.05) !important;
    border-color: rgba(255,255,255,0.3) !important; color: #ffffff !important;
}
.stButton > button[kind="primary"] {
    background: #ffffff !important; color: #000000 !important;
    border: none !important; font-weight: 600 !important;
}
.stButton > button[kind="primary"]:hover { background: rgba(255,255,255,0.85) !important; }
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: rgba(255,255,255,0.03) !important;
    border: 0.5px solid rgba(255,255,255,0.1) !important;
    border-radius: 8px !important; color: #e8e6e0 !important;
    font-family: 'Outfit', sans-serif !important; font-size: 13px !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: rgba(255,255,255,0.3) !important; box-shadow: none !important;
}
.stSelectbox > div > div {
    background: rgba(255,255,255,0.03) !important;
    border: 0.5px solid rgba(255,255,255,0.1) !important;
    border-radius: 8px !important; color: #e8e6e0 !important;
}
[data-testid="stTabs"] button {
    font-family: 'IBM Plex Mono', monospace !important; font-size: 11px !important;
    letter-spacing: 0.08em !important; text-transform: uppercase !important;
    color: rgba(255,255,255,0.35) !important; border: none !important;
    padding: 8px 16px !important;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    color: #ffffff !important; border-bottom: 1px solid #ffffff !important;
    background: transparent !important;
}
hr { border-color: rgba(255,255,255,0.06) !important; margin: 24px 0 !important; }
[data-testid="stAlert"] {
    background: rgba(255,255,255,0.03) !important;
    border: 0.5px solid rgba(255,255,255,0.08) !important;
    border-radius: 8px !important; font-size: 13px !important;
}
.stToggle > label {
    font-family: 'IBM Plex Mono', monospace !important; font-size: 11px !important;
    letter-spacing: 0.06em !important; color: rgba(255,255,255,0.5) !important;
    text-transform: uppercase !important;
}
.lf-mono {
    font-family: 'IBM Plex Mono', monospace; font-size: 11px;
    color: rgba(255,255,255,0.3); letter-spacing: 0.08em; text-transform: uppercase;
}
.parsed-card {
    background: rgba(255,255,255,0.02);
    border: 0.5px solid rgba(255,255,255,0.1);
    border-radius: 10px; padding: 14px 16px; margin-top: 10px;
}
.parsed-row {
    display: flex; justify-content: space-between;
    padding: 4px 0; border-bottom: 0.5px solid rgba(255,255,255,0.05);
    font-size: 12px;
}
.parsed-key {
    font-family: 'IBM Plex Mono', monospace; font-size: 10px;
    color: rgba(255,255,255,0.3); letter-spacing: 0.06em; text-transform: uppercase;
}
.parsed-val { color: rgba(255,255,255,0.7); font-size: 12px; text-align: right; max-width: 60%; }
.highlight-date {
    background: rgba(255,200,50,0.1); border: 0.5px solid rgba(255,200,50,0.2);
    color: #ffc832; padding: 1px 6px; border-radius: 4px;
    font-family: 'IBM Plex Mono', monospace; font-size: 10px; letter-spacing: 0.06em;
}
.highlight-company {
    background: rgba(100,200,255,0.08); border: 0.5px solid rgba(100,200,255,0.2);
    color: #64c8ff; padding: 1px 6px; border-radius: 4px;
    font-family: 'IBM Plex Mono', monospace; font-size: 10px; letter-spacing: 0.06em;
}
</style>
""", unsafe_allow_html=True)

init_db()


def load_drafts() -> list[dict]:
    if os.path.exists(DRAFTS_LOG):
        with open(DRAFTS_LOG) as f:
            try:
                return json.load(f)
            except Exception:
                return []
    return []


def clear_drafts_log():
    if os.path.exists(DRAFTS_LOG):
        os.remove(DRAFTS_LOG)


def is_gmail_connected() -> bool:
    return os.path.exists(TOKEN_FILE) and os.path.exists(CREDS_FILE)


def connect_gmail():
    try:
        get_gmail_service()
        return True
    except Exception as e:
        st.error(f"Gmail connection failed: {e}")
        return False


def disconnect_gmail():
    if os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)


# ─── TOP NAV ───────────────────────────────────────────────────────────────────
st.markdown("""
<div style="display:flex;align-items:center;justify-content:space-between;
            padding:18px 0;border-bottom:0.5px solid rgba(255,255,255,0.06);
            margin-bottom:32px;">
    <div style="display:flex;align-items:center;gap:12px;">
        <span style="font-family:'Syne',sans-serif;font-size:18px;font-weight:800;
                     letter-spacing:-0.03em;color:#ffffff;">LEADFLOW</span>
        <span style="font-family:'IBM Plex Mono',monospace;font-size:10px;
                     color:rgba(255,255,255,0.2);letter-spacing:0.1em;
                     border:0.5px solid rgba(255,255,255,0.1);
                     padding:2px 6px;border-radius:4px;">v1.0</span>
    </div>
    <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;
                color:rgba(255,255,255,0.2);letter-spacing:0.08em;">
        AUTONOMOUS LEAD INTELLIGENCE
    </div>
</div>
""", unsafe_allow_html=True)

stats           = get_stats()
drafts          = load_drafts()
gmail_connected = is_gmail_connected()

# ─── HERO + GMAIL ──────────────────────────────────────────────────────────────
col_hero, col_gmail = st.columns([3, 1])

with col_hero:
    st.markdown("""
    <div style="margin-bottom:8px;">
        <span style="font-family:'Syne',sans-serif;font-size:40px;font-weight:800;
                     letter-spacing:-0.04em;color:#ffffff;line-height:1.1;">
            Find. Score.<br>Outreach.
        </span>
    </div>
    <div style="font-family:'Outfit',sans-serif;font-size:14px;
                color:rgba(255,255,255,0.35);font-weight:300;margin-bottom:24px;">
        Describe what you want in plain English. The agent figures out where
        to search — JustDial, Eventbrite, IndiaMart, Sulekha, LinkedIn, and more.
        Dates, company names, locations — the more detail you give, the better.
    </div>
    """, unsafe_allow_html=True)

with col_gmail:
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    if gmail_connected:
        st.markdown("""
        <div style="background:rgba(77,255,143,0.05);border:0.5px solid rgba(77,255,143,0.2);
                    border-radius:10px;padding:14px 16px;text-align:center;">
            <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;
                        color:#4dff8f;letter-spacing:0.1em;margin-bottom:4px;">
                ● GMAIL CONNECTED</div>
            <div style="font-family:'Outfit',sans-serif;font-size:12px;
                        color:rgba(255,255,255,0.3);">Drafting enabled</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        if st.button("Disconnect Gmail", use_container_width=True):
            disconnect_gmail()
            st.rerun()
    else:
        st.markdown("""
        <div style="background:rgba(255,255,255,0.02);border:0.5px solid rgba(255,255,255,0.08);
                    border-radius:10px;padding:14px 16px;text-align:center;margin-bottom:8px;">
            <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;
                        color:rgba(255,255,255,0.25);letter-spacing:0.1em;margin-bottom:4px;">
                ○ GMAIL NOT CONNECTED</div>
            <div style="font-family:'Outfit',sans-serif;font-size:12px;
                        color:rgba(255,255,255,0.2);">Optional — connect to enable drafting</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Connect Gmail →", type="primary", use_container_width=True):
            if not os.path.exists(CREDS_FILE):
                st.error("credentials.json not found. Download from Google Cloud Console.")
            else:
                with st.spinner("Opening Gmail auth in browser..."):
                    success = connect_gmail()
                if success:
                    st.success("Gmail connected!")
                    st.rerun()

# ─── STATS ─────────────────────────────────────────────────────────────────────
st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total leads",  stats["total"])
c2.metric("HOT (85+)",    stats["hot"])
c3.metric("GOOD (60–84)", stats["good"])
c4.metric("Drafted",      stats["drafted"])
c5.metric("Ignored",      stats["ignored"])

st.divider()

# ─── MAIN LAYOUT ───────────────────────────────────────────────────────────────
col_config, col_results = st.columns([1, 3], gap="large")

with col_config:
    st.markdown('<div class="lf-mono" style="margin-bottom:12px;">Input mode</div>',
                unsafe_allow_html=True)
    mode = st.radio("", ["Natural language", "Manual ICP"],
                    label_visibility="collapsed", horizontal=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    if mode == "Natural language":
        st.markdown('<div class="lf-mono" style="margin-bottom:8px;">Describe your goal</div>',
                    unsafe_allow_html=True)
        st.markdown("""
        <div style="font-family:'Outfit',sans-serif;font-size:11px;
                    color:rgba(255,255,255,0.25);margin-bottom:8px;line-height:1.5;">
            Include: company name, location, dates, purpose, event type.<br>
            The more detail, the better the results.
        </div>
        """, unsafe_allow_html=True)

        nl_prompt = st.text_area(
            "",
            placeholder='e.g. "We have a Salon Booking App. We want leads of events and vendors in Delhi NCR where we can put our stall for Style Lounge. Offline events from 14th April to 30th April."',
            height=150,
            label_visibility="collapsed",
            key="nl_prompt"
        )

        if nl_prompt and len(nl_prompt) > 20:
            if st.button("Parse & analyse →", use_container_width=True):
                with st.spinner("AI analysing your goal..."):
                    parsed = parse_natural_language_prompt(nl_prompt)
                    st.session_state["parsed_icp"] = parsed

        # Show parsed result
        if "parsed_icp" in st.session_state and st.session_state["parsed_icp"]:
            p = st.session_state["parsed_icp"]

            # Build display rows
            rows = []
            if p.get("goal"):
                rows.append(("Goal", p["goal"]))
            if p.get("company_name"):
                rows.append(("Company", f'<span class="highlight-company">{p["company_name"]}</span>'))
            if p.get("lead_type"):
                rows.append(("Lead type", p["lead_type"]))
            if p.get("location"):
                rows.append(("Location", p["location"]))
            if p.get("date_range"):
                rows.append(("Dates", f'<span class="highlight-date">{p["date_range"]}</span>'))
            if p.get("purpose"):
                rows.append(("Purpose", p["purpose"]))
            if p.get("event_type"):
                rows.append(("Event type", p["event_type"]))

            rows_html = "".join([
                f'<div class="parsed-row"><span class="parsed-key">{k}</span>'
                f'<span class="parsed-val">{v}</span></div>'
                for k, v in rows
            ])

            st.markdown(f"""
            <div class="parsed-card">
                <div class="lf-mono" style="margin-bottom:10px;">Parsed intent</div>
                {rows_html}
            </div>
            """, unsafe_allow_html=True)

            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
            if st.button("Clear & re-parse", use_container_width=True):
                del st.session_state["parsed_icp"]
                st.rerun()

        icp_data = st.session_state.get("parsed_icp", {})

    else:
        st.markdown('<div class="lf-mono" style="margin-bottom:12px;">ICP</div>',
                    unsafe_allow_html=True)
        role     = st.text_input("Role",     value="Founder OR CEO OR VP Sales")
        industry = st.text_input("Industry", value="SaaS")
        location = st.text_input("Location", value="India")
        icp_data = {
            "goal":         f"Find {role} in {industry} in {location}",
            "lead_type":    "people",
            "industry":     industry,
            "location":     location,
            "role":         role,
            "context":      "",
            "company_name": None,
            "date_range":   None,
            "purpose":      "outreach",
            "event_type":   ""
        }

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    st.markdown('<div class="lf-mono" style="margin-bottom:12px;">Sender</div>',
                unsafe_allow_html=True)
    sender_name    = st.text_input("Your name", value="Arjun", placeholder="Your name")
    sender_product = st.text_area(
        "What you sell", height=70,
        value="An AI tool that finds qualified leads and writes personalised outreach"
    )

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    st.markdown('<div class="lf-mono" style="margin-bottom:12px;">Settings</div>',
                unsafe_allow_html=True)
    num_leads = st.slider("Leads to find", 5, 30, 10, 5)
    min_score = st.slider("Min qualify score", 0, 100, 60)

    if gmail_connected:
        auto_draft = st.toggle("Auto-draft HOT leads to Gmail", value=True)
    else:
        st.markdown("""
        <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;
                    color:rgba(255,255,255,0.2);padding:8px 0;letter-spacing:0.06em;">
            ○ AUTO-DRAFT — CONNECT GMAIL TO ENABLE
        </div>
        """, unsafe_allow_html=True)
        auto_draft = False

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    run_button = st.button("RUN AGENT →", type="primary", use_container_width=True)

    st.divider()
    st.markdown('<div class="lf-mono" style="margin-bottom:12px;">Danger zone</div>',
                unsafe_allow_html=True)
    if st.button("Delete all leads", use_container_width=True):
        delete_all_leads()
        st.success("All leads deleted")
        st.rerun()
    if st.button("Clear drafts log", use_container_width=True):
        clear_drafts_log()
        st.success("Drafts log cleared")
        st.rerun()

# ─── RIGHT: Results ────────────────────────────────────────────────────────────
with col_results:

    if run_button:
        if mode == "Natural language":
            icp_data = st.session_state.get("parsed_icp", {})
            if not icp_data:
                st.error("Please parse your prompt first — click 'Parse & analyse →'")
                st.stop()
        
        icp = {**icp_data, "product": sender_product}

        with st.status("Agent running...", expanded=True) as status:
            goal = icp.get("goal", "")
            dates = icp.get("date_range", "")
            company = icp.get("company_name", "")

            st.write(f"Goal: {goal}")
            if dates:
                st.write(f"Date range: {dates}")
            if company:
                st.write(f"Company: {company}")
            st.write("Strategy agent building multi-source search plan...")

            try:
                emails = run_email_agent(
                    icp=icp,
                    sender_name=sender_name,
                    sender_product=sender_product,
                    num_leads=num_leads
                )
                emails = [e for e in emails if e["score"] >= min_score]
                st.write(f"{len(emails)} qualified leads found, emails written...")

                if auto_draft and gmail_connected and emails:
                    st.write("Drafting HOT leads to Gmail...")
                    draft_all_emails(emails)
                    st.write("Drafts created!")

                status.update(
                    label=f"Done — {len(emails)} leads processed",
                    state="complete"
                )
                st.rerun()
            except Exception as e:
                st.error(f"Pipeline error: {e}")
                st.stop()

    all_leads     = get_all_leads()
    ignored_leads = get_ignored_leads()
    active_leads  = [l for l in all_leads if l["status"] != "ignored"]

    tab1, tab2, tab3 = st.tabs([
        f"LEADS  {len(active_leads)}",
        f"DRAFTS  {len(drafts)}",
        f"IGNORED  {len(ignored_leads)}"
    ])

    with tab1:
        if not active_leads:
            st.markdown("""
            <div style="text-align:center;padding:60px 20px;
                        border:0.5px solid rgba(255,255,255,0.06);
                        border-radius:12px;margin-top:16px;">
                <div style="font-family:'Syne',sans-serif;font-size:22px;
                            font-weight:700;color:rgba(255,255,255,0.15);margin-bottom:8px;">
                    No leads yet</div>
                <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;
                            color:rgba(255,255,255,0.12);letter-spacing:0.08em;">
                    Describe your goal and hit RUN AGENT →</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            fc1, fc2, fc3 = st.columns([1, 1, 2])
            with fc1:
                filter_tier = st.selectbox("", ["All", "HOT", "GOOD", "SKIP"],
                                           label_visibility="collapsed")
            with fc2:
                filter_status = st.selectbox("", ["All", "email_drafted", "scraped"],
                                             label_visibility="collapsed")
            with fc3:
                search_term = st.text_input("", placeholder="Search company...",
                                            label_visibility="collapsed")

            filtered = active_leads
            if filter_tier == "HOT":
                filtered = [l for l in filtered if l["score"] >= 85]
            elif filter_tier == "GOOD":
                filtered = [l for l in filtered if 60 <= l["score"] < 85]
            elif filter_tier == "SKIP":
                filtered = [l for l in filtered if l["score"] < 60]
            if filter_status != "All":
                filtered = [l for l in filtered if l["status"] == filter_status]
            if search_term:
                filtered = [l for l in filtered if search_term.lower() in l["company"].lower()]

            st.markdown(
                f'<div class="lf-mono" style="margin:8px 0 12px;">{len(filtered)} of {len(active_leads)} leads</div>',
                unsafe_allow_html=True
            )

            for lead in filtered:
                score       = lead["score"]
                tier        = "HOT" if score >= 85 else "GOOD" if score >= 60 else "SKIP"
                src         = lead.get("source_type", "")
                drafted_tag = "  · drafted" if lead["status"] == "email_drafted" else ""

                with st.expander(
                    f"{tier}  {score}/100  —  {lead['company']}  ·  {lead['estimated_role']}{drafted_tag}"
                ):
                    ca, cb = st.columns([3, 1])

                    with ca:
                        st.markdown(f"""
                        <div style="font-size:13px;color:rgba(255,255,255,0.55);
                                    margin-bottom:8px;line-height:1.6;">{lead['fit_reason']}</div>
                        """, unsafe_allow_html=True)

                        if lead.get("disqualify_reason"):
                            st.markdown(f"""
                            <div style="font-size:12px;color:rgba(255,100,100,0.6);
                                        margin-bottom:8px;">⚠ {lead['disqualify_reason']}</div>
                            """, unsafe_allow_html=True)

                        tags = []
                        if src:
                            tags.append(
                                f'<span style="font-family:IBM Plex Mono,monospace;font-size:10px;'
                                f'padding:2px 8px;border-radius:4px;background:rgba(255,255,255,0.05);'
                                f'color:rgba(255,255,255,0.35);border:0.5px solid rgba(255,255,255,0.08);">{src}</span>'
                            )
                        if lead["status"] == "email_drafted":
                            tags.append(
                                f'<span style="font-family:IBM Plex Mono,monospace;font-size:10px;'
                                f'padding:2px 8px;border-radius:4px;background:rgba(100,160,255,0.08);'
                                f'color:#6ba3ff;border:0.5px solid rgba(100,160,255,0.15);">drafted</span>'
                            )
                        if tags:
                            st.markdown(
                                f'<div style="display:flex;gap:6px;margin-bottom:8px;">{"".join(tags)}</div>',
                                unsafe_allow_html=True
                            )

                        st.markdown(
                            f'<div class="lf-mono" style="margin-top:4px;">Added {lead["created_at"][:10]}</div>',
                            unsafe_allow_html=True
                        )
                        if lead.get("link"):
                            st.markdown(f"[View source ↗]({lead['link']})")

                    with cb:
                        st.markdown(f"""
                        <div style="text-align:right;margin-bottom:16px;">
                            <div style="font-family:'Syne',sans-serif;font-size:32px;
                                        font-weight:800;color:#ffffff;line-height:1;">{score}</div>
                            <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;
                                        color:rgba(255,255,255,0.25);letter-spacing:0.08em;">/ 100</div>
                        </div>
                        """, unsafe_allow_html=True)

                        b1, b2 = st.columns(2)
                        with b1:
                            if st.button("Ignore", key=f"ig_{lead['id']}",
                                         use_container_width=True):
                                ignore_lead(lead["link"])
                                st.rerun()
                        with b2:
                            if st.button("Delete", key=f"dl_{lead['id']}",
                                         use_container_width=True, type="primary"):
                                delete_lead(lead["link"])
                                st.rerun()

    with tab2:
        if not gmail_connected:
            st.markdown("""
            <div style="text-align:center;padding:60px 20px;
                        border:0.5px solid rgba(255,255,255,0.06);
                        border-radius:12px;margin-top:16px;">
                <div style="font-family:'Syne',sans-serif;font-size:20px;
                            font-weight:700;color:rgba(255,255,255,0.15);margin-bottom:8px;">
                    Gmail not connected</div>
                <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;
                            color:rgba(255,255,255,0.12);letter-spacing:0.08em;">
                    Connect Gmail at the top of the page</div>
            </div>
            """, unsafe_allow_html=True)
        elif not drafts:
            st.info("No drafts yet. Run agent with Auto-draft HOT leads enabled.")
        else:
            st.markdown(f"""
            <div style="background:rgba(77,255,143,0.04);border:0.5px solid rgba(77,255,143,0.15);
                        border-radius:8px;padding:12px 16px;margin-bottom:16px;
                        font-family:'IBM Plex Mono',monospace;font-size:11px;
                        color:#4dff8f;letter-spacing:0.06em;">
                ● {len(drafts)} DRAFTS IN GMAIL —
                <a href="https://mail.google.com/mail/#drafts" target="_blank"
                   style="color:#4dff8f;text-decoration:underline;">OPEN GMAIL ↗</a>
            </div>
            """, unsafe_allow_html=True)
            for draft in drafts:
                with st.expander(f"{draft['company']} — {draft['subject']}"):
                    st.markdown(f"**To:** `{draft['to']}`")
                    st.markdown(f"**Subject:** {draft['subject']}")
                    st.markdown(f"**Draft ID:** `{draft['draft_id']}`")

    with tab3:
        if not ignored_leads:
            st.markdown("""
            <div style="text-align:center;padding:40px;font-family:'IBM Plex Mono',monospace;
                        font-size:11px;color:rgba(255,255,255,0.15);letter-spacing:0.08em;">
                NO IGNORED LEADS</div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(
                f'<div class="lf-mono" style="margin-bottom:12px;">{len(ignored_leads)} leads — never re-added</div>',
                unsafe_allow_html=True
            )
            for lead in ignored_leads:
                with st.expander(f"{lead['company']} · {lead['estimated_role']} — {lead['score']}/100"):
                    if lead.get("link"):
                        st.markdown(f"[View source ↗]({lead['link']})")
                    st.markdown(
                        f'<div class="lf-mono">Ignored {lead["created_at"][:10]}</div>',
                        unsafe_allow_html=True
                    )
                    if st.button("Restore", key=f"rs_{lead['id']}"):
                        restore_lead(lead["link"])
                        st.rerun()

# ─── EXPORT ────────────────────────────────────────────────────────────────────
all_leads    = get_all_leads()
active_leads = [l for l in all_leads if l["status"] != "ignored"]

if active_leads or drafts:
    st.divider()
    st.markdown('<div class="lf-mono" style="margin-bottom:12px;">Export</div>',
                unsafe_allow_html=True)
    ce1, ce2 = st.columns(2)
    with ce1:
        if active_leads:
            st.download_button(
                label="EXPORT LEADS →",
                data=json.dumps(active_leads, indent=2),
                file_name="leads_export.json",
                mime="application/json",
                use_container_width=True
            )
    with ce2:
        if drafts:
            st.download_button(
                label="EXPORT DRAFTS LOG →",
                data=json.dumps(drafts, indent=2),
                file_name="drafts_log.json",
                mime="application/json",
                use_container_width=True
            )

# ─── FOOTER ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="margin-top:48px;padding-top:24px;
            border-top:0.5px solid rgba(255,255,255,0.05);
            display:flex;justify-content:space-between;align-items:center;">
    <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;
                color:rgba(255,255,255,0.12);letter-spacing:0.08em;">
        LEADFLOW · AUTONOMOUS LEAD INTELLIGENCE</div>
    <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;
                color:rgba(255,255,255,0.12);letter-spacing:0.08em;">
        PYTHON · OPENAI · SERPER</div>
</div>
""", unsafe_allow_html=True)