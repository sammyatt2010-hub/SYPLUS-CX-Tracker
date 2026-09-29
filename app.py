import calendar
import hmac
import html as html_lib
import inspect
import re
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="SYPLUS CX Command Center", page_icon="🧭", layout="wide"
)

UK_TZ = ZoneInfo("Europe/London")


# --- Prospect Engine styling (design system shared across Sam's apps) ---
# Everything below to the "END styling" marker is presentation only — no
# business logic lives here. The dataframe grid's own colours can't be
# reached by CSS at all, which is why the matching dark theme also lives in
# .streamlit/config.toml alongside this file.
_PE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root{--bg:#0A0E1A;--surface:#111827;--surface-2:#161F33;--surface-3:#1C2740;--border:rgba(148,163,184,.14);--border-strong:rgba(148,163,184,.26);--text:#E7EAF3;--muted:#8C98B0;--faint:#5E6A82;--accent:#7C83FF;--accent-2:#38D6F5;--accent-soft:rgba(124,131,255,.14);--good:#34D399;--warn:#FBBF24;--risk:#FB923C;--bad:#F87171;--radius:14px;--grad:linear-gradient(135deg,#7C83FF 0%,#38D6F5 100%);}
html,body,[class*="css"],.stApp,button,input,textarea,select{font-family:'Inter',system-ui,-apple-system,'Segoe UI',sans-serif!important}
.stApp{background:radial-gradient(1200px 500px at 85% -10%,rgba(56,214,245,.07),transparent 60%),radial-gradient(900px 500px at 10% -20%,rgba(124,131,255,.10),transparent 60%),var(--bg)}
[data-testid="stHeader"]{background:transparent}[data-testid="stDecoration"]{display:none}footer{visibility:hidden}
.block-container{padding-top:1.6rem!important;padding-bottom:3rem!important;max-width:1500px}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#0D1322 0%,#0A0E1A 100%);border-right:1px solid var(--border)}
[data-testid="stWidgetLabel"] p{font-size:.76rem!important;font-weight:600!important;color:var(--muted)!important;text-transform:uppercase;letter-spacing:.06em}
[data-testid="stCaptionContainer"]{color:var(--muted)!important}
.st-key-card-login,.st-key-card-kpi,.st-key-card-matrix,.st-key-card-diary,.st-key-card-list{background:linear-gradient(180deg,rgba(22,31,51,.85) 0%,rgba(17,24,39,.85) 100%);border:1px solid var(--border)!important;border-radius:var(--radius);padding:22px 22px 18px;box-shadow:0 1px 0 rgba(255,255,255,.03) inset,0 20px 40px -24px rgba(0,0,0,.6);margin-bottom:18px}
[class*="st-key-appt-"],[class*="st-key-day-"]{background:linear-gradient(180deg,rgba(22,31,51,.7) 0%,rgba(17,24,39,.7) 100%);border:1px solid var(--border)!important;border-radius:12px;padding:14px 16px 10px;box-shadow:0 1px 0 rgba(255,255,255,.03) inset;margin-bottom:10px}
[data-baseweb="input"],[data-baseweb="select"]>div,[data-baseweb="textarea"]{background:var(--surface)!important;border:1px solid var(--border-strong)!important;border-radius:10px!important}
[data-baseweb="input"]:focus-within,[data-baseweb="select"]>div:focus-within,[data-baseweb="textarea"]:focus-within{border-color:var(--accent)!important;box-shadow:0 0 0 3px var(--accent-soft)!important}
[data-baseweb="input"]>div,[data-baseweb="base-input"]{background:transparent!important}
.stButton button,.stDownloadButton button,.stFormSubmitButton button{border-radius:10px!important;font-weight:600!important;border:1px solid var(--border-strong)!important;background:var(--surface-2)!important;color:var(--text)!important;transition:all .15s ease}
.stButton button:hover,.stDownloadButton button:hover{border-color:var(--accent)!important;transform:translateY(-1px)}
.stButton button[kind="primary"],.stDownloadButton button[kind="primary"],.stFormSubmitButton button,[data-testid="stBaseButton-primary"],[data-testid="stBaseLinkButton-primary"]{background:var(--grad)!important;border:none!important;color:#0A0E1A!important;box-shadow:0 8px 24px -10px rgba(124,131,255,.8)}
.stButton button[kind="primary"] p,[data-testid="stBaseButton-primary"] p,.stFormSubmitButton button p,[data-testid="stBaseLinkButton-primary"] p{color:#0A0E1A!important;font-weight:700!important}
[data-testid="stTabs"] [role="tablist"],[data-baseweb="tab-list"]{gap:4px;background:var(--surface);padding:4px;border-radius:12px;border:1px solid var(--border);width:fit-content}
[data-testid="stTabs"] [role="tab"],[data-baseweb="tab"]{border-radius:9px!important;padding:8px 16px!important;color:var(--muted)!important;background:transparent!important}
[data-testid="stTabs"] [role="tab"][aria-selected="true"],[data-baseweb="tab"][aria-selected="true"]{background:var(--surface-3)!important;color:var(--text)!important}
[data-baseweb="tab-highlight"],[data-baseweb="tab-border"],[data-testid="stTabs"] .react-aria-SelectionIndicator{display:none!important}
[data-testid="stDataFrame"]{border:1px solid var(--border);border-radius:12px;overflow:hidden}
[data-testid="stExpander"] details{background:var(--surface);border:1px solid var(--border)!important;border-radius:12px!important}
[data-testid="stAlert"]{border-radius:12px!important}
.pe-hero{display:flex;align-items:center;justify-content:space-between;gap:24px;flex-wrap:wrap;padding:6px 2px 22px;margin-bottom:18px;border-bottom:1px solid var(--border)}
.pe-eyebrow{display:inline-flex;align-items:center;gap:8px;font-size:.72rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--accent-2);margin-bottom:8px}
.pe-eyebrow .dot{width:7px;height:7px;border-radius:50%;background:var(--good);box-shadow:0 0 0 4px rgba(52,211,153,.15)}
.pe-title{font-size:2.05rem;font-weight:800;letter-spacing:-.035em;line-height:1.1;color:var(--text)}
.pe-title span{background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent}
.pe-sub{color:var(--muted);font-size:.95rem;margin-top:8px;max-width:620px}
.pe-section{display:flex;align-items:center;gap:12px;margin-bottom:16px;scroll-margin-top:20px}
.pe-section .badge{width:34px;height:34px;border-radius:10px;display:grid;place-items:center;background:var(--accent-soft);color:var(--accent);font-weight:800;font-size:.85rem;border:1px solid rgba(124,131,255,.3)}
.pe-section .t{font-size:1.08rem;font-weight:700;color:var(--text)}.pe-section .s{font-size:.82rem;color:var(--muted);margin-top:2px}
.pe-chip{display:inline-flex;align-items:center;gap:6px;padding:4px 10px;border-radius:999px;font-size:.76rem;font-weight:600;background:var(--surface-3);color:var(--text);border:1px solid var(--border);white-space:nowrap}
.pe-chip.accent{background:var(--accent-soft);color:#B9BDFF;border-color:rgba(124,131,255,.3)}
.pe-chip.good{background:rgba(52,211,153,.12);color:var(--good);border-color:rgba(52,211,153,.3)}
.pe-chip.warn{background:rgba(251,191,36,.12);color:var(--warn);border-color:rgba(251,191,36,.3)}
.pe-chip.bad{background:rgba(248,113,113,.12);color:var(--bad);border-color:rgba(248,113,113,.3)}
.pe-logo{width:40px;height:40px;border-radius:12px;background:var(--grad);display:grid;place-items:center;color:#0A0E1A;font-weight:800;box-shadow:0 10px 24px -10px rgba(124,131,255,.9)}
.pe-brand{display:flex;align-items:center;gap:12px;margin-bottom:6px}
.pe-brand .name{font-weight:800;color:var(--text);font-size:1rem;letter-spacing:-.02em}
.pe-brand .tag{color:var(--muted);font-size:.76rem}
.pe-status-row{display:flex;align-items:center;gap:8px;font-size:.82rem;color:var(--muted);margin:14px 0 18px}
.pe-status-row .dot{width:7px;height:7px;border-radius:50%;background:var(--good);box-shadow:0 0 0 3px rgba(52,211,153,.15)}
.pe-mini-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:18px}
.pe-mini{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:10px 12px}
.pe-mini .l{font-size:.66rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--faint)}
.pe-mini .v{font-size:1.25rem;font-weight:800;color:var(--text);margin-top:2px}
.pe-login-head{text-align:center;margin:6vh 0 22px}.pe-login-head .pe-logo{width:54px;height:54px;margin:0 auto 16px;border-radius:16px;font-size:1.1rem}
.pe-login-head .t{font-size:1.6rem;font-weight:800;letter-spacing:-.03em;color:var(--text)}.pe-login-head .s{color:var(--muted);font-size:.92rem;margin-top:6px}
.pe-kpi{background:var(--surface);border:1px solid var(--border);border-top:2px solid var(--accent);border-radius:14px;padding:16px 18px;height:100%}
.pe-kpi .l{font-size:.72rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.pe-kpi .v{font-size:1.8rem;font-weight:800;letter-spacing:-.03em;color:var(--text);margin-top:6px}
.pe-kpi-link{display:block;text-decoration:none!important;cursor:pointer;transition:all .15s ease}
.pe-kpi-link:hover{border-color:var(--accent);transform:translateY(-2px);box-shadow:0 10px 24px -12px rgba(124,131,255,.6)}
.pe-kpi-link .l,.pe-kpi-link .v{display:block}
.pe-kpi-link .v{color:var(--accent-2)!important}
</style>
"""
st.markdown(_PE_CSS, unsafe_allow_html=True)


def esc(v):
    """Escapes any scraped or user-typed text before it goes into HTML —
    skipping this is how an account called 'Smith & Co' breaks the page."""
    return html_lib.escape(str(v if v is not None else ""), quote=True)


def render_html(markup, target=None):
    # Flatten lines: indented HTML inside st.markdown would otherwise render
    # as a code block rather than as HTML.
    (target or st).markdown("".join(line.strip() for line in markup.splitlines()), unsafe_allow_html=True)


def chip(text, tone=""):
    return f'<span class="pe-chip {tone}">{esc(text)}</span>'


def section_header(num, title, subtitle="", anchor_id=None):
    id_attr = f' id="{esc(anchor_id)}"' if anchor_id else ""
    render_html(
        f'<div class="pe-section"{id_attr}><div class="badge">{num}</div><div><div class="t">{esc(title)}</div>'
        + (f'<div class="s">{esc(subtitle)}</div>' if subtitle else "")
        + "</div></div>"
    )


def _full_width():
    try:
        if "width" in inspect.signature(st.button).parameters:
            return {"width": "stretch"}
    except (TypeError, ValueError):
        pass
    return {"use_container_width": True}


FULL_WIDTH = _full_width()
# --- END styling helpers ---


# --- Simple password gate ---
def check_password():
    """Ask for a password before showing anything else on the page. The
    correct password lives in Streamlit secrets (app_password) rather than
    in this file, so it can be changed later without touching the code.
    Fails closed if that secret is missing (no accounts get in for free),
    and compares with hmac.compare_digest rather than == so the check can't
    leak timing information about the real password."""

    def password_entered():
        correct_password = st.secrets.get("app_password")
        entered_password = st.session_state.get("password_input", "")
        if correct_password and hmac.compare_digest(entered_password, correct_password):
            st.session_state["password_correct"] = True
            del st.session_state["password_input"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct"):
        return True

    render_html(
        '<div class="pe-login-head">'
        '<div class="pe-logo">SY</div>'
        '<div class="t">SYPLUS CX Command Center</div>'
        '<div class="s">Sign in to view live account &amp; diary data from Zoho CRM.</div>'
        "</div>"
    )
    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        with st.container(key="card-login"):
            st.text_input(
                "Password", type="password", on_change=password_entered, key="password_input"
            )
            if st.session_state.get("password_correct") is False:
                st.error("Incorrect password")
    return False


if not check_password():
    st.stop()


# The hero banner up top needs numbers (account count, last refreshed time)
# that aren't known until the Zoho data has loaded further down the script —
# st.empty() reserves its slot here, at the top of the page, and it's filled
# in later (see render_hero near the bottom) once those numbers exist.
hero_placeholder = st.empty()


def render_hero(target, account_count):
    render_html(
        '<div class="pe-hero"><div>'
        '<div class="pe-eyebrow"><span class="dot"></span> LIVE · ZOHO CRM</div>'
        '<div class="pe-title">SYPLUS Customer Experience <span>Command Center</span></div>'
        '<div class="pe-sub">SYPLUS accounts tagged for CX follow-up, ranked by eagerness '
        "and contract feasibility.</div></div>"
        '<div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center;">'
        + chip(f"{account_count} accounts tracked", "accent")
        + chip(f"Last refreshed {datetime.now(UK_TZ).strftime('%H:%M:%S')}")
        + "</div></div>",
        target=target,
    )

# --- Zoho CRM Connection & Loading ---
ZOHO_ACCOUNTS_URL = "https://accounts.zoho.eu/oauth/v2/token"
ZOHO_API_DOMAIN = "https://www.zohoapis.eu"
ACCOUNT_FIELDS = (
    "Account_Name,Tag,Phone,Post_Code,"
    "Primary_Contact_Name,Primary_Contact_Number,"
    "Contract_Date_End,Contact_Term,Network_Signed,No_of_Handsets"
)

# The SYPLUS "CX Filter" view in Zoho is built on these four tags. Any account
# carrying one of these (plus the SYPLUS tag) is what this wallboard tracks.
SYPLUS_TAG = "SYPLUS"

# A separate, independent tag consultants/account managers apply once they've
# booked a review visit — it sits alongside one of the four CX tags above
# rather than replacing it, so it's tracked as its own yes/no flag rather
# than as another entry in the eagerness ranking.
BOOKED_TAG = "CX - Review Booked"

# Eagerness ranking, highest priority first. Matches the colour-coding used
# on the tags inside Zoho (green / purple / yellow / red).
REAL_CX_TAGS = ["CX - Eager", "CX - Upgrade Potential", "CX - Review - Neutral", "CX - Leaving"]

# Not a real Zoho tag — a SYPLUS account with none of the four CX tags above
# still belongs on this wallboard (the account manager needs to see it), it
# just falls into this catch-all bucket instead of one of the four.
NO_CX_TAG = "No CX Tag"

EAGERNESS_ORDER = REAL_CX_TAGS + [NO_CX_TAG]
EAGERNESS_LABEL = {
    "CX - Eager": "Eager",
    "CX - Upgrade Potential": "Upgrade Potential",
    "CX - Review - Neutral": "Review – Neutral",
    "CX - Leaving": "Leaving (at risk)",
    NO_CX_TAG: "No CX Tag",
}

FEASIBILITY_ORDER = ["0–2 years", "2–4 years", "4–7 years", "7+ years", "Unknown"]

# Royal Mail's official UK postcode area codes and their head-town names —
# e.g. postcode "CH1 2AB" starts with area code "CH", which is Chester. This
# is a fixed, long-standing public reference list (unchanged for decades),
# not something to look up per-record, so it's derived locally rather than
# pulled from Zoho.
POSTCODE_AREA_NAMES = {
    "AB": "Aberdeen", "AL": "St Albans", "B": "Birmingham", "BA": "Bath",
    "BB": "Blackburn", "BD": "Bradford", "BH": "Bournemouth", "BL": "Bolton",
    "BN": "Brighton", "BR": "Bromley", "BS": "Bristol", "BT": "Belfast",
    "CA": "Carlisle", "CB": "Cambridge", "CF": "Cardiff", "CH": "Chester",
    "CM": "Chelmsford", "CO": "Colchester", "CR": "Croydon", "CT": "Canterbury",
    "CV": "Coventry", "CW": "Crewe", "DA": "Dartford", "DD": "Dundee",
    "DE": "Derby", "DG": "Dumfries", "DH": "Durham", "DL": "Darlington",
    "DN": "Doncaster", "DT": "Dorchester", "DY": "Dudley", "E": "East London",
    "EC": "East Central London", "EH": "Edinburgh", "EN": "Enfield",
    "EX": "Exeter", "FK": "Falkirk", "FY": "Blackpool", "G": "Glasgow",
    "GL": "Gloucester", "GU": "Guildford", "GY": "Guernsey", "HA": "Harrow",
    "HD": "Huddersfield", "HG": "Harrogate", "HP": "Hemel Hempstead",
    "HR": "Hereford", "HS": "Outer Hebrides", "HU": "Hull", "HX": "Halifax",
    "IG": "Ilford", "IM": "Isle of Man", "IP": "Ipswich", "IV": "Inverness",
    "JE": "Jersey", "KA": "Kilmarnock", "KT": "Kingston upon Thames",
    "KW": "Kirkwall", "KY": "Kirkcaldy", "L": "Liverpool", "LA": "Lancaster",
    "LD": "Llandrindod Wells", "LE": "Leicester", "LL": "Llandudno",
    "LN": "Lincoln", "LS": "Leeds", "LU": "Luton", "M": "Manchester",
    "ME": "Medway", "MK": "Milton Keynes", "ML": "Motherwell",
    "N": "North London", "NE": "Newcastle upon Tyne", "NG": "Nottingham",
    "NN": "Northampton", "NP": "Newport", "NR": "Norwich", "NW": "North West London",
    "OL": "Oldham", "OX": "Oxford", "PA": "Paisley", "PE": "Peterborough",
    "PH": "Perth", "PL": "Plymouth", "PO": "Portsmouth", "PR": "Preston",
    "RG": "Reading", "RH": "Redhill", "RM": "Romford", "S": "Sheffield",
    "SA": "Swansea", "SE": "South East London", "SG": "Stevenage",
    "SK": "Stockport", "SL": "Slough", "SM": "Sutton", "SN": "Swindon",
    "SO": "Southampton", "SP": "Salisbury", "SR": "Sunderland",
    "SS": "Southend-on-Sea", "ST": "Stoke-on-Trent", "SW": "South West London",
    "SY": "Shrewsbury", "TA": "Taunton", "TD": "Galashiels", "TF": "Telford",
    "TN": "Tonbridge", "TQ": "Torquay", "TR": "Truro", "TS": "Cleveland",
    "TW": "Twickenham", "UB": "Southall", "W": "West London", "WA": "Warrington",
    "WC": "West Central London", "WD": "Watford", "WF": "Wakefield",
    "WN": "Wigan", "WR": "Worcester", "WS": "Walsall", "WV": "Wolverhampton",
    "YO": "York", "ZE": "Lerwick",
}


def postcode_area_name(postcode):
    """Reads the postcode's leading area code (letters immediately before the
    first digit, e.g. 'CH' from 'CH1 2AB') and maps it to its Royal Mail area
    name. Returns '' for a blank, malformed, or unrecognised postcode rather
    than guessing."""
    if not postcode:
        return ""
    code = str(postcode).strip().upper().replace(" ", "")
    match = re.match(r"^([A-Z]{1,2})\d", code)
    if not match:
        return ""
    return POSTCODE_AREA_NAMES.get(match.group(1), "")

# Org ID for building direct "open this account in Zoho" links from the
# priority matrix. Zoho's own record URLs follow this pattern.
ZOHO_ORG_ID = "20098805637"


def zoho_account_url(account_id):
    return f"https://crm.zoho.eu/crm/org{ZOHO_ORG_ID}/tab/Accounts/{account_id}"


# --- Diary: booked visits, read live from Zoho's Meetings module ---
# The Zoho CRM UI calls this tab "Meetings" (see the left-hand nav), but its
# REST API module name is the standard "Events" — the same kind of UI-label
# vs api_name mismatch already hit with Legal Contracts (CustomModule4 ->
# Contracts) and Deals (Potentials -> Deals) earlier on. If this turns out to
# be wrong for this org, Zoho's own error message below will say so plainly
# (e.g. INVALID_MODULE) rather than failing silently.
EVENTS_MODULE = "Events"
EVENT_FIELDS = "Event_Title,Start_DateTime,End_DateTime,What_Id,Owner,Participants"

# Consultant availability isn't tracked as its own thing in Zoho — instead,
# the account manager marks a day directly in Zoho's calendar as an all-day
# Meeting titled with one of these keywords anywhere in it (against no
# account), and this app reads those back rather than needing anything new
# kept in sync. Two conventions are supported side by side: blocking out the
# (usually few) days a consultant is OUT — "Jamie - Unavailable" — or, often
# less typing overall, opening up the days they ARE free to book into —
# "Jamie - Available". "unavailable" is checked first since it contains
# "available" as a substring, so one keyword can't be mistaken for the other.
UNAVAILABLE_KEYWORD = "unavailable"
AVAILABLE_KEYWORD = "available"


def classify_availability_title(title):
    """Returns 'unavailable', 'available', or None for a Meeting title,
    per the keyword rules above."""
    t = (title or "").lower()
    if UNAVAILABLE_KEYWORD in t:
        return "unavailable"
    if AVAILABLE_KEYWORD in t:
        return "available"
    return None


def event_consultants(e):
    """Who an availability block actually belongs to. A consultant marking
    their own day just owns the Meeting themselves, so Owner is right. But
    an account manager booking it on a consultant's behalf — inviting them
    as a participant rather than owning it — means Owner is the account
    manager, not the consultant. So: every invited participant of type
    'user' except whoever owns the record, falling back to the Owner alone
    when that leaves nothing (the "marking your own day" case). This also
    means inviting several consultants to one block covers all of them."""
    owner = e.get("Owner") or {}
    owner_name = owner.get("name") if isinstance(owner, dict) else ""

    participants = e.get("Participants") or []
    names = {
        p.get("name")
        for p in participants
        if isinstance(p, dict) and p.get("type") == "user" and p.get("name")
    }
    names.discard(owner_name)

    if not names:
        names = {owner_name} if owner_name else {"Unknown"}
    return names


def format_duration(minutes):
    if minutes < 60:
        return f"{minutes} min"
    hours, rem = divmod(minutes, 60)
    return f"{hours}h" + (f" {rem}m" if rem else "")


@st.cache_data(ttl=60)
def load_meetings():
    """Pulls every Meeting (Zoho's 'Events' module) so booked visits can be
    matched back to the accounts they're linked to. Not filtered server-side
    by account — matching happens in Python once fetched, same pattern as
    everywhere else in this file."""
    token = get_access_token()
    headers = {"Authorization": f"Zoho-oauthtoken {token}"}

    records = []
    page = 1
    while True:
        try:
            resp = requests.get(
                f"{ZOHO_API_DOMAIN}/crm/v2/{EVENTS_MODULE}",
                headers=headers,
                params={
                    "fields": EVENT_FIELDS,
                    "per_page": 200,
                    "page": page,
                    "sort_by": "Start_DateTime",
                    "sort_order": "asc",
                },
                timeout=20,
            )
        except Exception as err:
            raise RuntimeError(f"Could not reach Zoho CRM API. Details: {err}")

        if resp.status_code == 204:
            break  # no meetings at all
        if resp.status_code != 200:
            raise RuntimeError(
                f"Zoho CRM API returned an error fetching Meetings "
                f"(status {resp.status_code}): {resp.text}"
            )

        payload = resp.json()
        records.extend(payload.get("data", []))
        info = payload.get("info", {})
        if not info.get("more_records"):
            break
        page += 1

    return records


@st.cache_data(ttl=60)
def load_deal_account_map():
    """Maps each Deal's id to its parent Account id, so a Meeting booked
    against a Deal record (rather than the Account itself) can still be
    matched back to the right account for the diary."""
    token = get_access_token()
    headers = {"Authorization": f"Zoho-oauthtoken {token}"}

    mapping = {}
    page = 1
    while True:
        try:
            resp = requests.get(
                f"{ZOHO_API_DOMAIN}/crm/v2/Deals",
                headers=headers,
                params={"fields": "Account_Name", "per_page": 200, "page": page},
                timeout=20,
            )
        except Exception:
            break  # best-effort — meetings booked directly against the Account still match
        if resp.status_code != 200:
            break

        payload = resp.json()
        for d in payload.get("data", []):
            account = d.get("Account_Name") or {}
            if d.get("id") and account.get("id"):
                mapping[d["id"]] = account["id"]

        if not payload.get("info", {}).get("more_records"):
            break
        page += 1

    return mapping


# Some accounts have never had a Contract End Date filled in on the Account
# record itself, but do have one on a "Legal Contracts" record underneath
# them (a separate related module — its real API name is "Contracts", the
# same UI-label-vs-api_name mismatch as Deals/Potentials). Verified live via
# Zoho's own API: the module's account lookup field is "Customer", and its
# end date field is "End_Date". An account can have more than one Legal
# Contract on file, so the latest (longest) End_Date is used.
LEGAL_CONTRACTS_MODULE = "Contracts"
LEGAL_CONTRACT_FIELDS = "Customer,End_Date"


@st.cache_data(ttl=60)
def load_legal_contract_end_dates():
    """Maps each Account id to the latest End_Date across its Legal
    Contracts records, as a fallback for accounts with no Contract End Date
    set directly on the Account. Raises on any Zoho-side error (wrong
    permissions/scope, module unreachable, etc.) rather than swallowing it —
    the caller decides how visible to make that, but it must never be
    invisible, or a real problem here (e.g. the connected app not being
    granted access to this module) looks identical to "nothing to fill in"."""
    token = get_access_token()
    headers = {"Authorization": f"Zoho-oauthtoken {token}"}

    latest_end_date = {}
    page = 1
    while True:
        try:
            resp = requests.get(
                f"{ZOHO_API_DOMAIN}/crm/v2/{LEGAL_CONTRACTS_MODULE}",
                headers=headers,
                params={"fields": LEGAL_CONTRACT_FIELDS, "per_page": 200, "page": page},
                timeout=20,
            )
        except Exception as err:
            raise RuntimeError(f"Could not reach Zoho CRM API for Legal Contracts. Details: {err}")

        if resp.status_code == 204:
            break  # no Legal Contracts records at all
        if resp.status_code != 200:
            raise RuntimeError(
                f"Zoho CRM API returned an error fetching Legal Contracts "
                f"(status {resp.status_code}): {resp.text}"
            )

        payload = resp.json()
        for c in payload.get("data", []):
            customer = c.get("Customer") or {}
            account_id = customer.get("id") if isinstance(customer, dict) else None
            end_date = pd.to_datetime(c.get("End_Date"), errors="coerce")
            if not account_id or pd.isna(end_date):
                continue
            if account_id not in latest_end_date or end_date > latest_end_date[account_id]:
                latest_end_date[account_id] = end_date

        if not payload.get("info", {}).get("more_records"):
            break
        page += 1

    return latest_end_date


def get_diary_appointments(accounts_df):
    """Resolves booked Meetings from Zoho into diary entries for the given
    accounts — matching each Meeting's What_Id against the account directly,
    or against one of its Deals. Returns (appointments, error_message); on
    failure, appointments is [] and error_message explains why, so the rest
    of the page can carry on rendering rather than crashing."""
    try:
        events = load_meetings()
    except Exception as err:
        return [], str(err)

    try:
        deal_to_account = load_deal_account_map()
    except Exception:
        deal_to_account = {}

    account_ids = set(accounts_df["Account ID"])
    account_names = dict(zip(accounts_df["Account ID"], accounts_df["Account Name"]))
    account_postcodes = dict(zip(accounts_df["Account ID"], accounts_df["Postal Code"]))

    appointments = []
    for e in events:
        title = e.get("Event_Title") or ""
        if classify_availability_title(title) is not None:
            continue  # an availability marker, not a real booked visit

        what = e.get("What_Id") or {}
        related_id = what.get("id") if isinstance(what, dict) else None
        if not related_id:
            continue

        account_id = related_id if related_id in account_ids else deal_to_account.get(related_id)
        if account_id not in account_ids:
            continue  # not linked to one of our tracked accounts

        start_dt = pd.to_datetime(e.get("Start_DateTime"), errors="coerce")
        if pd.isna(start_dt):
            continue
        end_dt = pd.to_datetime(e.get("End_DateTime"), errors="coerce")
        if pd.isna(end_dt):
            end_dt = start_dt + timedelta(minutes=30)

        owner = e.get("Owner") or {}
        consultant = owner.get("name") if isinstance(owner, dict) else ""

        appointments.append(
            {
                "id": e.get("id"),
                "account_id": account_id,
                "account_name": account_names.get(account_id, ""),
                "postcode": account_postcodes.get(account_id, "") or "",
                "title": e.get("Event_Title") or "Review Visit",
                "consultant": consultant or "",
                "date": start_dt.date().isoformat(),
                "time": start_dt.strftime("%H:%M"),
                "start_dt": start_dt,
                "end_dt": end_dt,
            }
        )

    return appointments, None


def get_availability_blocks():
    """Reads consultant availability markers straight from Zoho's Meetings —
    any Meeting titled 'Unavailable' or 'Available' (see classify_
    availability_title above), regardless of what account (if any) it's
    booked against. A block spanning several days only needs one Meeting in
    Zoho: every calendar date from its start to its end (inclusive) counts,
    for whoever it belongs to (see event_consultants above — the invited
    consultant if an account manager booked it on their behalf, or the
    owner if a consultant marked their own day). Returns ({date_iso:
    {"available": {names}, "unavailable": {names}}}, error_message)."""
    try:
        events = load_meetings()
    except Exception as err:
        return {}, str(err)

    blocks_by_date = {}
    for e in events:
        title = e.get("Event_Title") or ""
        kind = classify_availability_title(title)
        if kind is None:
            continue

        start_dt = pd.to_datetime(e.get("Start_DateTime"), errors="coerce")
        if pd.isna(start_dt):
            continue
        end_dt = pd.to_datetime(e.get("End_DateTime"), errors="coerce")
        if pd.isna(end_dt):
            end_dt = start_dt

        consultants = event_consultants(e)

        day = start_dt.date()
        last_day = end_dt.date()
        while day <= last_day:
            day_entry = blocks_by_date.setdefault(
                day.isoformat(), {"available": set(), "unavailable": set()}
            )
            day_entry[kind] |= consultants
            day += timedelta(days=1)

    return blocks_by_date, None


def add_months(d, delta):
    month_index = d.month - 1 + delta
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def render_appointment(appt):
    """Renders one diary entry: time, title, account, the site postcode
    (so consultants' areas are easy to spot at a glance), and the
    consultant it's booked with. Read-only — these come straight from
    Zoho, so cancelling or rescheduling happens there, not in this view."""
    start_dt = appt["start_dt"]
    end_dt = appt["end_dt"]
    with st.container(key=f"appt-{appt['id']}"):
        account_link = zoho_account_url(appt["account_id"])
        duration_minutes = int((end_dt - start_dt).total_seconds() // 60)
        postcode_suffix = f" · 📍 {appt['postcode']}" if appt.get("postcode") else ""
        st.markdown(
            f"**{appt['time']}** — [{appt['account_name']}]({account_link}){postcode_suffix}  \n"
            f"_{appt['title']}"
            + (f" ({format_duration(duration_minutes)})_" if duration_minutes > 0 else "_")
        )
        if appt["consultant"]:
            st.caption(f"👤 {appt['consultant']}")


@st.cache_data(ttl=270)  # Zoho access tokens last 1hr; refresh well before that
def get_access_token():
    try:
        creds = st.secrets["zoho"]
    except Exception as err:
        raise RuntimeError(
            f"Missing Zoho credentials in Streamlit secrets. Details: {err}"
        )

    try:
        resp = requests.post(
            ZOHO_ACCOUNTS_URL,
            data={
                "grant_type": "refresh_token",
                "client_id": creds["client_id"],
                "client_secret": creds["client_secret"],
                "refresh_token": creds["refresh_token"],
            },
            timeout=15,
        )
        payload = resp.json()
    except Exception as err:
        raise RuntimeError(f"Could not reach Zoho accounts server. Details: {err}")

    token = payload.get("access_token")
    if not token:
        raise RuntimeError(f"Zoho authentication failed: {payload}")
    return token


@st.cache_data(ttl=60)
def load_accounts():
    token = get_access_token()
    headers = {"Authorization": f"Zoho-oauthtoken {token}"}

    records = []
    page = 1
    while True:
        try:
            resp = requests.get(
                f"{ZOHO_API_DOMAIN}/crm/v2/Accounts",
                headers=headers,
                params={
                    "fields": ACCOUNT_FIELDS,
                    "per_page": 200,
                    "page": page,
                    "sort_by": "Modified_Time",
                    "sort_order": "desc",
                },
                timeout=20,
            )
        except Exception as err:
            raise RuntimeError(f"Could not reach Zoho CRM API. Details: {err}")

        if resp.status_code == 204:
            break  # no data at all
        if resp.status_code != 200:
            raise RuntimeError(
                f"Zoho CRM API returned an error (status {resp.status_code}): {resp.text}"
            )

        payload = resp.json()
        records.extend(payload.get("data", []))
        info = payload.get("info", {})
        if not info.get("more_records"):
            break
        page += 1

    rows = []
    for r in records:
        tag_names = [t.get("name", "") for t in (r.get("Tag") or [])]

        # Only accounts explicitly tagged SYPLUS belong on this wallboard.
        if SYPLUS_TAG not in tag_names:
            continue

        # Pick the highest-priority CX tag present on this account. A SYPLUS
        # account with none of the four still needs to be visible to the
        # account manager, so it falls into the NO_CX_TAG bucket rather than
        # being dropped.
        cx_tag = next((t for t in REAL_CX_TAGS if t in tag_names), None) or NO_CX_TAG

        rows.append(
            {
                "Account ID": r.get("id"),
                "Account Name": r.get("Account_Name") or "",
                "CX Tag": cx_tag,
                # Placeholder — overwritten below from real Zoho Meetings once
                # they're loaded, which is the actual source of truth.
                "Booked": BOOKED_TAG in tag_names,
                "All Tags": ", ".join(sorted(tag_names)),
                "Primary Contact": r.get("Primary_Contact_Name") or "",
                "Primary Contact Number": r.get("Primary_Contact_Number") or "",
                "Phone": r.get("Phone") or "",
                "Postal Code": r.get("Post_Code") or "",
                "Contract Signed": r.get("Network_Signed") or "",
                "Contract Term (months)": r.get("Contact_Term"),
                "Contract End Date": r.get("Contract_Date_End") or "",
                "No. of Handsets": r.get("No_of_Handsets"),
            }
        )

    return pd.DataFrame(rows)


@st.cache_data(ttl=600)  # site contacts change far less often than CX tags — cache longer
def get_contacts_lookup():
    """Fall back for accounts with no Primary Contact set directly, from their
    linked Contact records. Pulls the whole Contacts module in bulk (a handful
    of paginated requests) rather than one request per account — much faster
    than looking up each account's contacts one at a time. Picks whichever
    linked contact has a mobile or phone number on file (preferring mobile),
    so the number is one someone can actually ring."""
    token = get_access_token()
    headers = {"Authorization": f"Zoho-oauthtoken {token}"}

    contacts_by_account_id = {}
    page = 1
    while True:
        try:
            resp = requests.get(
                f"{ZOHO_API_DOMAIN}/crm/v2/Contacts",
                headers=headers,
                params={
                    "fields": "Account_Name,Full_Name,Phone,Mobile",
                    "per_page": 200,
                    "page": page,
                },
                timeout=20,
            )
        except Exception:
            break  # contacts are a nice-to-have; don't sink the whole page over this

        if resp.status_code != 200:
            break  # 204 = no contacts at all; anything else, stop quietly

        payload = resp.json()
        for c in payload.get("data", []):
            account = c.get("Account_Name") or {}
            account_id = account.get("id")
            if not account_id:
                continue
            contacts_by_account_id.setdefault(account_id, []).append(c)

        if not payload.get("info", {}).get("more_records"):
            break
        page += 1

    contacts_by_account = {}
    for account_id, contacts in contacts_by_account_id.items():
        best = next((c for c in contacts if c.get("Mobile")), None)
        if best is None:
            best = next((c for c in contacts if c.get("Phone")), contacts[0])
        contacts_by_account[account_id] = {
            "name": best.get("Full_Name") or "",
            "number": best.get("Mobile") or best.get("Phone") or "",
        }

    return contacts_by_account


# --- Load & Error Handling ---
try:
    df = load_accounts()
except Exception as e:
    st.error(f"🚨 Zoho CRM Connection Error: {e}")
    st.stop()

if df.empty:
    st.warning(
        "No SYPLUS accounts were found. Check that accounts in Zoho carry the "
        "**SYPLUS** tag."
    )
    st.stop()

# Fill in a site contact for any account with no Primary Contact set directly
# on the Account record, from that account's linked Contact records.
try:
    contacts_lookup = get_contacts_lookup()
except Exception:
    contacts_lookup = {}

needs_lookup = df["Primary Contact"] == ""
for account_id, contact in contacts_lookup.items():
    mask = needs_lookup & (df["Account ID"] == account_id)
    df.loc[mask, "Primary Contact"] = contact["name"]
    df.loc[mask, "Primary Contact Number"] = contact["number"]

# Pull real booked Meetings from Zoho now (rather than down in the Diary
# section) so the top-line KPI and Priority Matrix reflect an actual booking
# the moment it's made in Zoho. This is the single source of truth for
# "booked" — the old "CX - Review Booked" tag was a manual stand-in from
# before meetings were tracked in Zoho itself, and is no longer read here,
# so it can't drift out of sync with what's really on the calendar.
try:
    appointments, diary_error = get_diary_appointments(df)
except Exception as err:
    appointments, diary_error = [], str(err)

booked_account_ids = {a["account_id"] for a in appointments}
df["Booked"] = df["Account ID"].isin(booked_account_ids)


# --- Data Prep: contract end date, time remaining, feasibility tier ---
def parse_zoho_date(value):
    """Zoho returns Contract End Date as a formula-driven string, and the
    signed date as a plain date string. Both use ISO-style yyyy-MM-dd."""
    if not value:
        return pd.NaT
    try:
        return pd.to_datetime(value, errors="coerce")
    except Exception:
        return pd.NaT


df["Contract End Date"] = df["Contract End Date"].apply(parse_zoho_date)
df["End Date Source"] = "Account record"

# Fall back to the Legal Contracts related module for any account that has
# no Contract End Date set directly on the Account itself — some colleagues
# have been filling contract dates in there instead of on the main Account
# page. Only fills gaps; an end date already on the Account record is left
# as-is.
try:
    legal_contract_end_dates = load_legal_contract_end_dates()
    legal_contracts_error = None
except Exception as err:
    legal_contract_end_dates = {}
    legal_contracts_error = str(err)

if legal_contracts_error:
    st.warning(
        f"⚠️ Couldn't pull Legal Contracts end dates from Zoho, so accounts "
        f"relying on that fallback still show 'Unknown' for now. Details: "
        f"{legal_contracts_error}"
    )

missing_end_date = df["Contract End Date"].isna()
for account_id, end_date in legal_contract_end_dates.items():
    mask = missing_end_date & (df["Account ID"] == account_id)
    df.loc[mask, "Contract End Date"] = end_date
    df.loc[mask, "End Date Source"] = "Legal Contracts"

today = pd.Timestamp(datetime.now(UK_TZ).date())
df["Days Remaining"] = (df["Contract End Date"] - today).dt.days


def feasibility_tier(days):
    if pd.isna(days):
        return "Unknown"
    if days <= 365 * 2:  # includes contracts already ended
        return "0–2 years"
    if days <= 365 * 4:
        return "2–4 years"
    if days <= 365 * 7:
        return "4–7 years"
    return "7+ years"


def time_remaining_label(days):
    if pd.isna(days):
        return "No end date on file"
    days = int(days)
    if days < 0:
        return f"Overdue by {abs(days) // 30} mo" if abs(days) >= 30 else f"Overdue by {abs(days)}d"
    years, rem_days = divmod(days, 365)
    months = rem_days // 30
    if years == 0 and months == 0:
        return f"{days}d left"
    parts = []
    if years:
        parts.append(f"{years}y")
    if months:
        parts.append(f"{months}m")
    return " ".join(parts) + " left"


df["Feasibility"] = df["Days Remaining"].apply(feasibility_tier)
df["Time Remaining"] = df["Days Remaining"].apply(time_remaining_label)
df["Eagerness"] = df["CX Tag"].map(EAGERNESS_LABEL)
df["Area"] = df["Postal Code"].apply(postcode_area_name)
df["Booked Status"] = df["Booked"].map({True: "Booked", False: "Not booked"})


# --- Sidebar: brand, live snapshot, filters ---
render_html(
    '<div class="pe-brand"><div class="pe-logo">SY</div><div>'
    '<div class="name">SYPLUS CX</div><div class="tag">Customer Experience Command Center</div>'
    "</div></div>",
    target=st.sidebar,
)
render_html(
    '<div class="pe-status-row"><span class="dot"></span> Connected to Zoho CRM</div>',
    target=st.sidebar,
)
render_html(
    '<div class="pe-mini-grid">'
    f'<div class="pe-mini"><div class="l">Tracked</div><div class="v">{len(df)}</div></div>'
    f'<div class="pe-mini"><div class="l">Booked</div><div class="v">{int(df["Booked"].sum())}</div></div>'
    f'<div class="pe-mini"><div class="l">No CX Tag</div><div class="v">{int((df["CX Tag"] == NO_CX_TAG).sum())}</div></div>'
    f'<div class="pe-mini"><div class="l">Leaving</div><div class="v">{int((df["CX Tag"] == "CX - Leaving").sum())}</div></div>'
    "</div>",
    target=st.sidebar,
)

st.sidebar.header("Filters")

selected_cx_tags = st.sidebar.multiselect(
    "CX Tag", options=EAGERNESS_ORDER, default=EAGERNESS_ORDER,
    format_func=lambda t: EAGERNESS_LABEL[t],
)
selected_feasibility = st.sidebar.multiselect(
    "Feasibility (time left on contract)",
    options=FEASIBILITY_ORDER,
    default=FEASIBILITY_ORDER,
)
selected_booked_status = st.sidebar.multiselect(
    "Review visit",
    options=["Booked", "Not booked"],
    default=["Booked", "Not booked"],
)
name_search = st.sidebar.text_input("Search account name")

st.sidebar.divider()
if st.sidebar.button("Refresh data now", type="primary", **FULL_WIDTH):
    st.cache_data.clear()
    st.rerun()
st.sidebar.caption(f"Last refreshed: {datetime.now(UK_TZ).strftime('%d/%m/%Y %H:%M:%S')}")
st.sidebar.caption("Data refreshes from Zoho CRM automatically every 60 seconds, or click the button above for an instant refresh.")

st.sidebar.divider()
if st.sidebar.button("Log out", **FULL_WIDTH):
    st.session_state["password_correct"] = False
    st.rerun()

filtered_df = df[
    df["CX Tag"].isin(selected_cx_tags)
    & df["Feasibility"].isin(selected_feasibility)
    & df["Booked Status"].isin(selected_booked_status)
]
if name_search:
    filtered_df = filtered_df[
        filtered_df["Account Name"].str.contains(name_search, case=False, na=False)
    ]

# --- Top-Line KPIs ---
with st.container(key="card-kpi"):
    section_header(1, "Overview", "Live counts across your filtered SYPLUS accounts")

    kpi_cols = st.columns(len(EAGERNESS_ORDER) + 2)
    with kpi_cols[0]:
        render_html(f'<div class="pe-kpi"><div class="l">SYPLUS Accounts Tracked</div><div class="v">{len(filtered_df)}</div></div>')
    for col, tag in zip(kpi_cols[1:-1], EAGERNESS_ORDER):
        with col:
            render_html(f'<div class="pe-kpi"><div class="l">{esc(EAGERNESS_LABEL[tag])}</div><div class="v">{len(filtered_df[filtered_df["CX Tag"] == tag])}</div></div>')
    filtered_account_ids = set(filtered_df["Account ID"])
    appointment_count = sum(1 for a in appointments if a["account_id"] in filtered_account_ids)
    with kpi_cols[-1]:
        # Clickable straight through to the Diary below — Sam's users would
        # rather click than filter/sort the Full Account List table by hand.
        render_html(
            '<a href="#diary-section" class="pe-kpi pe-kpi-link">'
            '<span class="l">Booked Appointments ↓</span>'
            f'<span class="v">{appointment_count}</span></a>'
        )

# --- Eagerness x Feasibility Matrix ---
with st.container(key="card-matrix"):
    section_header(
        2, "Priority Matrix",
        "Eagerness (from CX tag, or 'No CX Tag' where none is set yet) down the side, "
        "feasibility (time left on contract) across the top. The top-left corner is "
        "where to focus first.",
    )

    MATRIX_FEASIBILITY = ["0–2 years", "2–4 years", "4–7 years"]
    HOTTEST_CELL = ("CX - Eager", "0–2 years")  # eager + contract ending soon = act now

    header_cols = st.columns([1.3] + [1] * len(MATRIX_FEASIBILITY))
    header_cols[0].markdown("**Eagerness \\ Feasibility**")
    for c, feas in zip(header_cols[1:], MATRIX_FEASIBILITY):
        c.markdown(f"**{feas}**")

    for tag in EAGERNESS_ORDER:
        row_cols = st.columns([1.3] + [1] * len(MATRIX_FEASIBILITY))
        row_cols[0].markdown(f"**{EAGERNESS_LABEL[tag]}**")
        for c, feas in zip(row_cols[1:], MATRIX_FEASIBILITY):
            cell_df = filtered_df[
                (filtered_df["CX Tag"] == tag) & (filtered_df["Feasibility"] == feas)
            ].sort_values("Days Remaining")
            with c:
                with st.container(border=True):
                    badge = "🔥 " if (tag, feas) == HOTTEST_CELL else ""
                    st.markdown(f"{badge}**{len(cell_df)}**")
                    booked_count = int(cell_df["Booked"].sum())
                    if booked_count:
                        st.caption(f"📅 {booked_count} booked")
                    if not cell_df.empty:
                        with st.popover("View accounts", use_container_width=True):
                            for _, acc in cell_df.iterrows():
                                contact = acc["Primary Contact"] or "No primary contact on file"
                                account_link = zoho_account_url(acc["Account ID"])
                                booked_marker = " · 📅 Booked" if acc["Booked"] else ""
                                st.markdown(
                                    f"**[{acc['Account Name']}]({account_link})** — "
                                    f"{acc['Time Remaining']}{booked_marker}  \n"
                                    f"_{contact}_"
                                )

    unknown_df = filtered_df[filtered_df["Feasibility"] == "Unknown"].copy()
    if not unknown_df.empty:
        unknown_df["Open in Zoho"] = unknown_df["Account ID"].apply(zoho_account_url)
        with st.expander(
            f"⚠️ {len(unknown_df)} account(s) with no contract end date on file"
        ):
            st.dataframe(
                unknown_df[
                    ["Account Name", "CX Tag", "Primary Contact", "Contract Term (months)", "Open in Zoho"]
                ],
                hide_index=True,
                use_container_width=True,
                column_config={"Open in Zoho": st.column_config.LinkColumn(display_text="Open ↗")},
            )

    # The matrix above only shows up to 4–7 years since no contract currently
    # runs longer — but if one ever does, it's flagged here rather than
    # silently dropped.
    long_df = filtered_df[filtered_df["Feasibility"] == "7+ years"].copy()
    if not long_df.empty:
        long_df["Open in Zoho"] = long_df["Account ID"].apply(zoho_account_url)
        with st.expander(
            f"ℹ️ {len(long_df)} account(s) with more than 7 years left on contract"
        ):
            st.dataframe(
                long_df[["Account Name", "CX Tag", "Time Remaining", "Primary Contact", "Open in Zoho"]],
                hide_index=True,
                use_container_width=True,
                column_config={"Open in Zoho": st.column_config.LinkColumn(display_text="Open ↗")},
            )

# --- Diary View ---
with st.container(key="card-diary"):
    section_header(
        3, "Diary — Booked Review Visits",
        "Live from Zoho's Meetings — booked against an account or one of its deals. "
        "Cancelling or rescheduling happens in Zoho itself; this just reflects it.",
        anchor_id="diary-section",
    )

    if diary_error:
        st.error(f"🚨 Could not load Meetings from Zoho: {diary_error}")

    availability_by_date, availability_error = get_availability_blocks()
    if availability_error:
        st.error(f"🚨 Could not load consultant availability from Zoho: {availability_error}")

    def consultant_of(appt):
        return appt["consultant"] or "Unknown"

    consultant_options = {consultant_of(a) for a in appointments}
    for entry in availability_by_date.values():
        consultant_options |= entry["available"] | entry["unavailable"]
    consultant_options = sorted(consultant_options)

    selected_consultants = st.multiselect(
        "Filter by consultant",
        options=consultant_options,
        default=consultant_options,
        key="diary_consultant_filter",
    )
    diary_appointments = [a for a in appointments if consultant_of(a) in selected_consultants]

    st.caption(
        "✅ = marked available to book that day in Zoho (a Meeting titled with "
        "'Available' in it) · 🚫 = marked unavailable ('Unavailable' in the "
        "title). Either way, check the existing bookings shown for that day "
        "before booking in — this doesn't check for clashes automatically."
    )

    def availability_markers(day_iso):
        """Renders the available/unavailable chips for one diary day, filtered
        to the selected consultants. A consultant with both an 'Available' and
        an 'Unavailable' marker on the same day (unusual, but possible) shows
        under both — Zoho is the source of truth, so this just reflects
        whatever's there rather than trying to arbitrate between them."""
        entry = availability_by_date.get(day_iso, {"available": set(), "unavailable": set()})
        available_today = sorted(entry["available"] & set(selected_consultants))
        unavailable_today = sorted(entry["unavailable"] & set(selected_consultants))
        if available_today:
            render_html(chip("✅ " + ", ".join(available_today), "good"))
        if unavailable_today:
            render_html(chip("🚫 " + ", ".join(unavailable_today), "bad"))

    appointments_by_date = {}
    for appt in diary_appointments:
        appointments_by_date.setdefault(appt["date"], []).append(appt)
    for day_appts in appointments_by_date.values():
        day_appts.sort(key=lambda a: a["time"])

    if "diary_ref_date" not in st.session_state:
        st.session_state["diary_ref_date"] = date.today()

    view_mode = st.radio("View", options=["Week", "Month"], horizontal=True, key="diary_view_mode")

    nav_cols = st.columns([1, 1, 1, 4])
    if nav_cols[0].button("Previous", **FULL_WIDTH):
        if view_mode == "Week":
            st.session_state["diary_ref_date"] -= timedelta(days=7)
        else:
            st.session_state["diary_ref_date"] = add_months(st.session_state["diary_ref_date"], -1)
    if nav_cols[1].button("Today", **FULL_WIDTH):
        st.session_state["diary_ref_date"] = date.today()
    if nav_cols[2].button("Next", **FULL_WIDTH):
        if view_mode == "Week":
            st.session_state["diary_ref_date"] += timedelta(days=7)
        else:
            st.session_state["diary_ref_date"] = add_months(st.session_state["diary_ref_date"], 1)

    ref_date = st.session_state["diary_ref_date"]

    if view_mode == "Week":
        week_start = ref_date - timedelta(days=ref_date.weekday())
        week_days = [week_start + timedelta(days=i) for i in range(7)]
        st.caption(f"Week of {week_start.strftime('%d %b %Y')}")

        day_cols = st.columns(7)
        for col, day in zip(day_cols, week_days):
            with col:
                is_today = day == date.today()
                st.markdown(f"{'🔵 ' if is_today else ''}**{day.strftime('%a %d %b')}**")
                availability_markers(day.isoformat())
                day_appts = appointments_by_date.get(day.isoformat(), [])
                if not day_appts:
                    st.caption("—")
                else:
                    for appt in day_appts:
                        render_appointment(appt)
    else:
        st.caption(ref_date.strftime("%B %Y"))
        weeks = calendar.monthcalendar(ref_date.year, ref_date.month)

        header_cols = st.columns(7)
        for col, day_name in zip(header_cols, ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
            col.markdown(f"**{day_name}**")

        for week_idx, week in enumerate(weeks):
            week_cols = st.columns(7)
            for col_idx, (col, day_num) in enumerate(zip(week_cols, week)):
                with col:
                    with st.container(key=f"day-{ref_date.year}-{ref_date.month}-{week_idx}-{col_idx}"):
                        if day_num == 0:
                            st.markdown("&nbsp;")
                            continue
                        day_date = date(ref_date.year, ref_date.month, day_num)
                        is_today = day_date == date.today()
                        st.markdown(f"{'🔵 ' if is_today else ''}**{day_num}**")
                        availability_markers(day_date.isoformat())
                        day_appts = appointments_by_date.get(day_date.isoformat(), [])
                        if day_appts:
                            with st.popover(f"{len(day_appts)} 📅", use_container_width=True):
                                for appt in day_appts:
                                    render_appointment(appt)

# --- Full Sortable List ---
with st.container(key="card-list"):
    section_header(4, "Full Account List", "Sorted by days remaining on contract")
    full_list_df = filtered_df.sort_values("Days Remaining").copy()
    full_list_df["Open in Zoho"] = full_list_df["Account ID"].apply(zoho_account_url)
    st.dataframe(
        full_list_df[
            [
                "Account Name",
                "Eagerness",
                "Booked",
                "Feasibility",
                "Time Remaining",
                "Contract End Date",
                "End Date Source",
                "Postal Code",
                "Area",
                "Primary Contact",
                "Primary Contact Number",
                "Open in Zoho",
            ]
        ],
        hide_index=True,
        use_container_width=True,
        column_config={
            "Contract End Date": st.column_config.DateColumn(format="DD/MM/YYYY"),
            "End Date Source": st.column_config.TextColumn(
                "End Date Source",
                help="Where this end date came from: the Account record itself, or (when that's blank) the latest Legal Contracts record underneath it.",
            ),
            "Booked": st.column_config.CheckboxColumn(
                "Booked", help="Ticked once a review visit has been booked (CX - Review Booked tag)"
            ),
            "Open in Zoho": st.column_config.LinkColumn(display_text="Open ↗"),
        },
    )

# Fill in the hero banner reserved at the top of the page now that the
# account count for this run is known.
render_hero(hero_placeholder, len(df))
