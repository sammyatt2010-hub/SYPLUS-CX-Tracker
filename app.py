from datetime import datetime

import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="SYPLUS CX Command Center", page_icon="🧭", layout="wide"
)
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


@st.cache_data(ttl=300)  # site contacts change far less often than CX tags — cache longer
def get_related_contacts(account_ids):
    """For accounts with no Primary Contact set directly, fall back to their
    linked Contact records. Picks whichever linked contact has a mobile or
    phone number on file (preferring mobile), so the number is one someone
    can actually ring."""
    token = get_access_token()
    headers = {"Authorization": f"Zoho-oauthtoken {token}"}
    contacts_by_account = {}

    for account_id in account_ids:
        try:
            resp = requests.get(
                f"{ZOHO_API_DOMAIN}/crm/v2/Accounts/{account_id}/Contacts",
                headers=headers,
                params={"fields": "Full_Name,Phone,Mobile"},
                timeout=15,
            )
        except Exception:
            continue  # one account failing to reach Zoho shouldn't sink the page

        if resp.status_code != 200:
            continue  # 204 = no linked contacts; anything else, skip quietly

        contacts = resp.json().get("data", [])
        if not contacts:
            continue

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
needs_lookup = df.loc[df["Primary Contact"] == "", "Account ID"].dropna().tolist()
if needs_lookup:
    try:
        related = get_related_contacts(tuple(needs_lookup))
    except Exception:
        related = {}
    for account_id, contact in related.items():
        mask = df["Account ID"] == account_id
        df.loc[mask, "Primary Contact"] = contact["name"]
        df.loc[mask, "Primary Contact Number"] = contact["number"]


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
today = pd.Timestamp(datetime.now().date())
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
name_search = st.sidebar.text_input("Search account name")

st.sidebar.divider()
st.sidebar.caption(f"Last refreshed: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
st.sidebar.caption("Data refreshes from Zoho CRM automatically every 60 seconds.")

filtered_df = df[
    df["CX Tag"].isin(selected_cx_tags)
    & df["Feasibility"].isin(selected_feasibility)
]
if name_search:
    filtered_df = filtered_df[
        filtered_df["Account Name"].str.contains(name_search, case=False, na=False)
    ]

st.divider()

# --- Top-Line KPIs ---

kpi_cols = st.columns(len(EAGERNESS_ORDER) + 1)
kpi_cols[0].metric("SYPLUS Accounts Tracked", f"{len(filtered_df)}")
for col, tag in zip(kpi_cols[1:], EAGERNESS_ORDER):
    col.metric(EAGERNESS_LABEL[tag], f"{len(filtered_df[filtered_df['CX Tag'] == tag])}")

st.divider()

# --- Eagerness x Feasibility Matrix ---
st.subheader("🎯 Priority Matrix")
st.caption(
    "Eagerness (from CX tag) down the side, feasibility (time left on contract) "
    "across the top. The top-left corner is where to focus first."
)

MATRIX_FEASIBILITY = ["< 12 months", "1–3 years", "3–7 years", "7+ years"]
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
                if not cell_df.empty:
                    with st.popover("View accounts", use_container_width=True):
                        for _, acc in cell_df.iterrows():
                            contact = acc["Primary Contact"] or "No primary contact on file"
                            st.markdown(
                                f"**{acc['Account Name']}** — {acc['Time Remaining']}  \n"
                                f"_{contact}_"
                            )

unknown_df = filtered_df[filtered_df["Feasibility"] == "Unknown"]
if not unknown_df.empty:
    with st.expander(
        f"⚠️ {len(unknown_df)} account(s) with no contract end date on file"
    ):
        st.dataframe(
            unknown_df[["Account Name", "CX Tag", "Primary Contact", "Contract Term (months)"]],
            hide_index=True,
            use_container_width=True,
        )

st.divider()

# --- Full Sortable List ---
st.subheader("📋 Full Account List")
st.dataframe(
    filtered_df.sort_values("Days Remaining")[
        [
            "Account Name",
            "Eagerness",
            "Feasibility",
            "Time Remaining",
            "Contract End Date",
            "Primary Contact",
            "Primary Contact Number",
            "No. of Handsets",
            "All Tags",
        ]
    ],
    hide_index=True,
    use_container_width=True,
    column_config={
        "Contract End Date": st.column_config.DateColumn(format="DD/MM/YYYY"),
    },
)
