import calendar
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


# --- Simple password gate ---
def check_password():
    """Ask for a password before showing anything else on the page. The
    correct password lives in Streamlit secrets (app_password) rather than
    in this file, so it can be changed later without touching the code."""

    def password_entered():
        if st.session_state.get("password_input") == st.secrets.get("app_password", ""):
            st.session_state["password_correct"] = True
            del st.session_state["password_input"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct"):
        return True

    st.text_input(
        "🔒 Password", type="password", on_change=password_entered, key="password_input"
    )
    if st.session_state.get("password_correct") is False:
        st.error("Incorrect password")
    return False


if not check_password():
    st.stop()


st.title("🧭 SYPLUS Customer Experience Command Center")
st.caption(
    "Live from Zoho CRM — SYPLUS accounts tagged for CX follow-up, "
    "ranked by eagerness and contract feasibility."
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
EAGERNESS_ORDER = ["CX - Eager", "CX - Upgrade Potential", "CX - Review - Neutral", "CX - Leaving"]
EAGERNESS_LABEL = {
    "CX - Eager": "Eager",
    "CX - Upgrade Potential": "Upgrade Potential",
    "CX - Review - Neutral": "Review – Neutral",
    "CX - Leaving": "Leaving (at risk)",
}

FEASIBILITY_ORDER = ["< 12 months", "1–3 years", "3–7 years", "7+ years", "Unknown"]

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
EVENT_FIELDS = "Event_Title,Start_DateTime,End_DateTime,What_Id,Owner"


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

    appointments = []
    for e in events:
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
                "title": e.get("Event_Title") or "Review Visit",
                "consultant": consultant or "",
                "date": start_dt.date().isoformat(),
                "time": start_dt.strftime("%H:%M"),
                "start_dt": start_dt,
                "end_dt": end_dt,
            }
        )

    return appointments, None


def add_months(d, delta):
    month_index = d.month - 1 + delta
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def render_appointment(appt):
    """Renders one diary entry: time, title, account, and the consultant
    it's booked with. Read-only — these come straight from Zoho, so
    cancelling or rescheduling happens there, not in this view."""
    start_dt = appt["start_dt"]
    end_dt = appt["end_dt"]
    with st.container(border=True):
        account_link = zoho_account_url(appt["account_id"])
        duration_minutes = int((end_dt - start_dt).total_seconds() // 60)
        st.markdown(
            f"**{appt['time']}** — [{appt['account_name']}]({account_link})  \n"
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

        # Pick the highest-priority CX tag present on this account, if any.
        cx_tag = next((t for t in EAGERNESS_ORDER if t in tag_names), None)
        if cx_tag is None:
            continue  # SYPLUS account with no CX status tag yet — not actionable here

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
        "No SYPLUS accounts with a CX tag were found. Check that accounts in Zoho "
        "carry both the **SYPLUS** tag and one of the CX status tags "
        "(CX - Eager, CX - Upgrade Potential, CX - Review - Neutral, CX - Leaving)."
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
today = pd.Timestamp(datetime.now(UK_TZ).date())
df["Days Remaining"] = (df["Contract End Date"] - today).dt.days


def feasibility_tier(days):
    if pd.isna(days):
        return "Unknown"
    if days <= 365:  # includes contracts already ended
        return "< 12 months"
    if days <= 365 * 3:
        return "1–3 years"
    if days <= 365 * 7:
        return "3–7 years"
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


# --- Sidebar Filters ---
st.sidebar.header("🔍 Filters")

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
if st.sidebar.button("🔄 Refresh data now", use_container_width=True):
    st.cache_data.clear()
    st.rerun()
st.sidebar.caption(f"Last refreshed: {datetime.now(UK_TZ).strftime('%d/%m/%Y %H:%M:%S')}")
st.sidebar.caption("Data refreshes from Zoho CRM automatically every 60 seconds, or click the button above for an instant refresh.")

filtered_df = df[
    df["CX Tag"].isin(selected_cx_tags)
    & df["Feasibility"].isin(selected_feasibility)
    & df["Booked Status"].isin(selected_booked_status)
]
if name_search:
    filtered_df = filtered_df[
        filtered_df["Account Name"].str.contains(name_search, case=False, na=False)
    ]

st.divider()

# --- Top-Line KPIs ---

kpi_cols = st.columns(len(EAGERNESS_ORDER) + 2)
kpi_cols[0].metric("SYPLUS Accounts Tracked", f"{len(filtered_df)}")
for col, tag in zip(kpi_cols[1:-1], EAGERNESS_ORDER):
    col.metric(EAGERNESS_LABEL[tag], f"{len(filtered_df[filtered_df['CX Tag'] == tag])}")
filtered_account_ids = set(filtered_df["Account ID"])
appointment_count = sum(1 for a in appointments if a["account_id"] in filtered_account_ids)
kpi_cols[-1].metric("📅 Booked Appointments", f"{appointment_count}")

st.divider()

# --- Eagerness x Feasibility Matrix ---
st.subheader("🎯 Priority Matrix")
st.caption(
    "Eagerness (from CX tag) down the side, feasibility (time left on contract) "
    "across the top. The top-left corner is where to focus first."
)

MATRIX_FEASIBILITY = ["< 12 months", "1–3 years", "3–7 years"]
HOTTEST_CELL = ("CX - Eager", "< 12 months")  # eager + contract ending soon = act now

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

# The matrix above only shows up to 3–7 years since no contract currently runs
# longer — but if one ever does, it's flagged here rather than silently dropped.
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

st.divider()

# --- Diary View ---
st.subheader("🗓️ Diary — Booked Review Visits")
st.caption(
    "Live from Zoho's Meetings — booked against an account or one of its "
    "deals. Cancelling or rescheduling happens in Zoho itself; this just "
    "reflects it."
)

if diary_error:
    st.error(f"🚨 Could not load Meetings from Zoho: {diary_error}")

appointments_by_date = {}
for appt in appointments:
    appointments_by_date.setdefault(appt["date"], []).append(appt)
for day_appts in appointments_by_date.values():
    day_appts.sort(key=lambda a: a["time"])

if "diary_ref_date" not in st.session_state:
    st.session_state["diary_ref_date"] = date.today()

view_mode = st.radio("View", options=["Week", "Month"], horizontal=True, key="diary_view_mode")

nav_cols = st.columns([1, 1, 1, 4])
if nav_cols[0].button("◀ Previous", use_container_width=True):
    if view_mode == "Week":
        st.session_state["diary_ref_date"] -= timedelta(days=7)
    else:
        st.session_state["diary_ref_date"] = add_months(st.session_state["diary_ref_date"], -1)
if nav_cols[1].button("Today", use_container_width=True):
    st.session_state["diary_ref_date"] = date.today()
if nav_cols[2].button("Next ▶", use_container_width=True):
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

    for week in weeks:
        week_cols = st.columns(7)
        for col, day_num in zip(week_cols, week):
            with col:
                with st.container(border=True):
                    if day_num == 0:
                        st.markdown("&nbsp;")
                        continue
                    day_date = date(ref_date.year, ref_date.month, day_num)
                    is_today = day_date == date.today()
                    st.markdown(f"{'🔵 ' if is_today else ''}**{day_num}**")
                    day_appts = appointments_by_date.get(day_date.isoformat(), [])
                    if day_appts:
                        with st.popover(f"{len(day_appts)} 📅", use_container_width=True):
                            for appt in day_appts:
                                render_appointment(appt)

st.divider()

# --- Full Sortable List ---
st.subheader("📋 Full Account List")
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
        "Booked": st.column_config.CheckboxColumn(
            "Booked", help="Ticked once a review visit has been booked (CX - Review Booked tag)"
        ),
        "Open in Zoho": st.column_config.LinkColumn(display_text="Open ↗"),
    },
)
