import datetime
import io
import re
import pandas as pd
from PIL import Image
import pytesseract
import streamlit as st

st.set_page_config(page_title="User Budget & ID Tracker", layout="wide")

# ==========================================
# 1. OCR & TEXT PARSER
# ==========================================
def parse_email_text(raw_text: str) -> dict:
    # Email ID
    email_match = re.search(
        r'Email\s*ID\s*:\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        raw_text,
        re.IGNORECASE,
    )
    if email_match:
        email_id = email_match.group(1).strip()
    else:
        fallback = re.findall(
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', raw_text
        )
        email_id = fallback[0] if fallback else ""

    # Requester
    requester_match = re.search(
        r'(?:To\s*:?\s*|To\s+)([A-Za-z\s\.]+?)(?=\s+(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\b|\s+Cc\b|;|\n|\r|$)',
        raw_text,
        re.IGNORECASE,
    )
    requester = requester_match.group(1).strip() if requester_match else ""
    requester = re.sub(
        r'\s+(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)$', '', requester, flags=re.IGNORECASE
    ).strip()

    # Display Name
    display_match = re.search(
        r'Display\s*Name\s*:\s*([^\n\r]+)', raw_text, re.IGNORECASE
    )
    display_name = display_match.group(1).strip() if display_match else ""

    # Request Number
    request_match = re.search(r'##RE-\d+##', raw_text)
    request_number = request_match.group(0) if request_match else ""

    # Date (DD-MM-YYYY to YYYY/MM/DD)
    date_match = re.search(r'\b(\d{2})[-/](\d{2})[-/](\d{4})\b', raw_text)
    if date_match:
        day, month, year = date_match.group(1), date_match.group(2), date_match.group(3)
        when_created = f"{year}/{month}/{day}"
    else:
        when_created = datetime.date.today().strftime("%Y/%m/%d")

    # Budget Status
    budget_match = re.search(r'\b(Budgeted|Unbudgeted)\b', raw_text, re.IGNORECASE)
    budget_info = budget_match.group(1).capitalize() if budget_match else "Budgeted"

    return {
        "email_id": email_id,
        "display_name": display_name,
        "request_number": request_number,
        "requester": requester,
        "when_created": when_created,
        "budget_info": budget_info,
    }


# ==========================================
# 2. SESSION STATE
# ==========================================
if "entries" not in st.session_state:
    st.session_state["entries"] = []  # List of dicts (failsafe)

if "parsed_data" not in st.session_state:
    st.session_state["parsed_data"] = {
        "email_id": "",
        "display_name": "",
        "request_number": "",
        "requester": "",
        "when_created": datetime.date.today().strftime("%Y/%m/%d"),
        "budget_info": "Budgeted",
    }


# ==========================================
# 3. SIDEBAR BUDGET TRACKER
# ==========================================
st.sidebar.title("⚙️ Budget Settings")
st.sidebar.markdown("Customize total allotted budget per location:")

budget_ggn = st.sidebar.number_input("GGN Budget", min_value=0, value=30, step=1)
budget_msr = st.sidebar.number_input("MSR Budget", min_value=0, value=25, step=1)
budget_pune = st.sidebar.number_input("Pune Budget", min_value=0, value=15, step=1)

budget_limits = {"GGN": budget_ggn, "MSR": budget_msr, "Pune": budget_pune}

# Count usage from entries list
used_counts = {}
for entry in st.session_state["entries"]:
    loc = entry.get("Location", "")
    used_counts[loc] = used_counts.get(loc, 0) + 1

st.sidebar.markdown("---")
st.sidebar.title("📊 Budget Tracker Summary")

for loc in ["GGN", "MSR", "Pune"]:
    total = budget_limits[loc]
    used = used_counts.get(loc, 0)
    remaining = total - used
    st.sidebar.metric(
        label=f"Location: {loc}",
        value=f"{remaining} Left",
        delta=f"{used} Used of {total}",
    )


# ==========================================
# 4. MAIN UI
# ==========================================
st.title("User Budget & ID Tracker")

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Upload Screenshot")
    uploaded_file = st.file_uploader("Upload screenshot (PNG, JPG)", type=["png", "jpg", "jpeg"])

    if uploaded_file is not None:
        st.image(uploaded_file, caption="Uploaded Email Image", use_column_width=True)

        if st.button("Extract Data from Image", type="primary"):
            with st.spinner("Extracting text via OCR..."):
                try:
                    image = Image.open(uploaded_file)
                    extracted_text = pytesseract.image_to_string(image)
                    st.session_state["parsed_data"] = parse_email_text(extracted_text)
                    st.success("Extraction Complete!")
                except Exception as e:
                    st.error(f"OCR Error: {e}")

with col2:
    st.subheader("2. Extracted Details & Manual Inputs")

    req_num_val = st.text_input("Request Number", value=st.session_state["parsed_data"]["request_number"])
    budget_val = st.selectbox(
        "Budget Status",
        ["Budgeted", "Unbudgeted"],
        index=0 if st.session_state["parsed_data"]["budget_info"] == "Budgeted" else 1,
    )
    requester_val = st.text_input("Requester", value=st.session_state["parsed_data"]["requester"])
    email_val = st.text_input("UPN / Email ID", value=st.session_state["parsed_data"]["email_id"])
    display_val = st.text_input("Display Name", value=st.session_state["parsed_data"]["display_name"])
    created_val = st.text_input("When Created", value=st.session_state["parsed_data"]["when_created"])
    location_val = st.selectbox("Location", ["GGN", "MSR", "Pune"])

    if st.button("Save & Log to Sheet", type="primary"):
        if not req_num_val or not email_val:
            st.error("Please ensure Request Number and Email ID are provided.")
        else:
            new_entry = {
                "Request Number": req_num_val,
                "Budget Status": budget_val,
                "Requester": requester_val,
                "UPN / Email ID": email_val,
                "Display Name": display_val,
                "When Created": created_val,
                "Location": location_val,
            }
            st.session_state["entries"].append(new_entry)
            st.success(f"Entry saved under {location_val}!")


# ==========================================
# 5. EXCEL LOG & DOWNLOAD
# ==========================================
st.markdown("---")
st.subheader("📋 Maintained Excel Entries Log")

if len(st.session_state["entries"]) > 0:
    df_entries = pd.DataFrame(st.session_state["entries"])
    st.dataframe(df_entries, use_container_width=True)

    # Prepare Excel download
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_entries.to_excel(writer, index=False, sheet_name="ID_Tracker")
    excel_data = buffer.getvalue()

    col_dl1, col_dl2 = st.columns([1, 4])
    with col_dl1:
        st.download_button(
            label="📥 Download Excel Sheet (.xlsx)",
            data=excel_data,
            file_name=f"ID_Tracker_Log_{datetime.date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    with col_dl2:
        if st.button("Clear All Logged Entries"):
            st.session_state["entries"] = []
            st.rerun()
else:
    st.info("No entries logged yet. Extract details above and click 'Save & Log to Sheet'.")
