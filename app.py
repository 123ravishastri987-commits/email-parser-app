import datetime
import io
import re
import pandas as pd
from PIL import Image
import pytesseract
import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="User Budget & ID Tracker", layout="wide")

# ==========================================
# 1. GOOGLE SHEETS LIVE CONNECTION
# ==========================================
using_gsheets = False
df_existing = pd.DataFrame()

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_existing = conn.read(worksheet="Sheet1", ttl=0)
    if df_existing is None or df_existing.empty:
        df_existing = pd.DataFrame(
            columns=[
                "Request Number",
                "User Type",
                "Budget Status",
                "Requester",
                "UPN / Email ID",
                "Display Name",
                "When Created",
                "Location",
            ]
        )
    using_gsheets = True
except Exception as e:
    st.sidebar.error(f"⚠️ GSheets Connection Not Active:\n{e}")
    if "entries" not in st.session_state:
        st.session_state["entries"] = []
    df_existing = pd.DataFrame(st.session_state["entries"])


# ==========================================
# 2. PERSISTENT REQUESTER LIST MANAGEMENT
# ==========================================
default_requester_list = ["Tushar Agrawal", "Vikram Singh", "Keshav Saini", "Other"]

if "custom_requesters" not in st.session_state:
    if using_gsheets:
        try:
            df_req = conn.read(worksheet="Requesters", ttl=0)
            if df_req is not None and not df_req.empty and "Requester Name" in df_req.columns:
                st.session_state["custom_requesters"] = df_req["Requester Name"].dropna().tolist()
            else:
                st.session_state["custom_requesters"] = default_requester_list
        except Exception:
            st.session_state["custom_requesters"] = default_requester_list
    else:
        st.session_state["custom_requesters"] = default_requester_list


# ==========================================
# 3. OCR & PARSER LOGIC
# ==========================================
def parse_email_text(raw_text: str) -> dict:
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

    requester_match = re.search(
        r'(?:To\s*:?\s*|To\s+)([A-Za-z\s\.]+?)(?=\s+(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\b|\s+Cc\b|;|\n|\r|$)',
        raw_text,
        re.IGNORECASE,
    )
    requester = requester_match.group(1).strip() if requester_match else ""
    requester = re.sub(
        r'\s+(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)$', '', requester, flags=re.IGNORECASE
    ).strip()

    display_match = re.search(
        r'Display\s*Name\s*:\s*([^\n\r]+)', raw_text, re.IGNORECASE
    )
    display_name = display_match.group(1).strip() if display_match else ""

    request_match = re.search(r'##RE-\d+##', raw_text)
    request_number = request_match.group(0) if request_match else ""

    date_match = re.search(r'\b(\d{2})[-/](\d{2})[-/](\d{4})\b', raw_text)
    if date_match:
        day, month, year = (
            date_match.group(1),
            date_match.group(2),
            date_match.group(3),
        )
        when_created = f"{year}/{month}/{day}"
    else:
        when_created = datetime.date.today().strftime("%Y/%m/%d")

    budget_match = re.search(
        r'\b(Budgeted|Unbudgeted)\b', raw_text, re.IGNORECASE
    )
    budget_info = (
        budget_match.group(1).capitalize() if budget_match else "Budgeted"
    )

    return {
        "email_id": email_id,
        "display_name": display_name,
        "request_number": request_number,
        "requester": requester,
        "when_created": when_created,
        "budget_info": budget_info,
    }


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
# 4. SIDEBAR: BUDGET & REQUESTER SETTINGS
# ==========================================
st.sidebar.title("⚙️ Budget Settings")
st.sidebar.markdown("Customize total allotted budget per location:")

budget_ggn = st.sidebar.number_input("GGN Budget", min_value=0, value=30, step=1)
budget_msr = st.sidebar.number_input("MSR Budget", min_value=0, value=25, step=1)
budget_pune = st.sidebar.number_input("Pune Budget", min_value=0, value=15, step=1)

budget_limits = {"GGN": budget_ggn, "MSR": budget_msr, "Pune": budget_pune}

st.sidebar.markdown("---")
st.sidebar.title("👥 Requester Options")
st.sidebar.markdown("Add or edit requester names for the dropdown (one name per line):")

requesters_text_current = "\n".join(st.session_state["custom_requesters"])

user_requesters_raw = st.sidebar.text_area(
    "Custom Requester List", value=requesters_text_current, height=140
)

if st.sidebar.button("💾 Save Requester List"):
    updated_list = [name.strip() for name in user_requesters_raw.split("\n") if name.strip()]
    st.session_state["custom_requesters"] = updated_list
    
    if using_gsheets:
        try:
            df_req_to_save = pd.DataFrame({"Requester Name": updated_list})
            conn.update(worksheet="Requesters", data=df_req_to_save)
            st.sidebar.success("Saved permanently to Google Sheets!")
        except Exception as e:
            st.sidebar.error(f"Could not save to Sheet: {e}")
    else:
        st.sidebar.success("Saved for current session!")
    st.rerun()

used_counts = (
    df_existing["Location"].value_counts().to_dict()
    if not df_existing.empty and "Location" in df_existing.columns
    else {}
)

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
# 5. MAIN INTERFACE
# ==========================================
st.title("User Budget & ID Tracker")

if using_gsheets:
    st.success("🟢 Connected to Google Sheets (Cloud Sync Active)")
else:
    st.warning("🟡 Running in Temporary Mode (Google Sheets credentials missing)")

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Upload Screenshot")
    uploaded_file = st.file_uploader(
        "Upload screenshot (PNG, JPG)", type=["png", "jpg", "jpeg"]
    )

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

    req_num_val = st.text_input(
        "Request Number", value=st.session_state["parsed_data"]["request_number"]
    )
    
    # MANUAL OPTION: User Type (New / Replacement)
    user_type_val = st.selectbox("User Type", ["New", "Replacement"], index=0)

    budget_val = st.selectbox(
        "Budget Status",
        ["Budgeted", "Unbudgeted"],
        index=0 if st.session_state["parsed_data"]["budget_info"] == "Budgeted" else 1,
    )

    # REQUESTER OPTION: OCR vs Dropdown
    requester_mode = st.radio(
        "Requester Input Method",
        ["Extracted from Photo (OCR)", "Select from Dropdown"],
        horizontal=True,
    )

    if requester_mode == "Extracted from Photo (OCR)":
        requester_val = st.text_input(
            "Requester Name", value=st.session_state["parsed_data"]["requester"]
        )
    else:
        requester_val = st.selectbox("Select Requester Name", options=st.session_state["custom_requesters"])

    email_val = st.text_input(
        "UPN / Email ID", value=st.session_state["parsed_data"]["email_id"]
    )
    display_val = st.text_input(
        "Display Name", value=st.session_state["parsed_data"]["display_name"]
    )
    created_val = st.text_input(
        "When Created", value=st.session_state["parsed_data"]["when_created"]
    )
    location_val = st.selectbox("Location", ["GGN", "MSR", "Pune"])

    if st.button("Save & Log to Sheet", type="primary"):
        if not req_num_val or not email_val:
            st.error("Please ensure Request Number and Email ID are provided.")
        else:
            new_row = pd.DataFrame(
                [
                    {
                        "Request Number": req_num_val,
                        "User Type": user_type_val,
                        "Budget Status": budget_val,
                        "Requester": requester_val,
                        "UPN / Email ID": email_val,
                        "Display Name": display_val,
                        "When Created": created_val,
                        "Location": location_val,
                    }
                ]
            )

            if using_gsheets:
                updated_df = pd.concat([df_existing, new_row], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_df)
                st.success(f"Entry permanently saved to Google Sheets under {location_val}!")
            else:
                st.session_state["entries"].append(new_row.to_dict("records")[0])
                st.success(f"Entry saved temporarily under {location_val}!")
            st.rerun()


# ==========================================
# 6. ENTRIES LOG, DELETE, & EXCEL DOWNLOAD
# ==========================================
st.markdown("---")
st.subheader("📋 Maintained Entries Log")

if not df_existing.empty:
    st.dataframe(df_existing, use_container_width=True)

    col_dl1, col_dl2 = st.columns([1, 1])

    with col_dl1:
        st.markdown("#### 📥 Download Copy")
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_existing.to_excel(writer, index=False, sheet_name="ID_Tracker")
        excel_data = buffer.getvalue()

        st.download_button(
            label="Download Excel Copy (.xlsx)",
            data=excel_data,
            file_name=f"ID_Tracker_Log_{datetime.date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    with col_dl2:
        st.markdown("#### 🗑️ Delete Specific Entry")
        delete_options = [
            f"Row {idx + 1}: {row.get('Request Number', '')} | {row.get('Display Name', '')}"
            for idx, row in df_existing.iterrows()
        ]
        selected_entry_to_delete = st.selectbox("Select entry to remove:", options=delete_options)

        if st.button("Delete Selected Entry", type="secondary"):
            row_idx_to_delete = int(selected_entry_to_delete.split(":")[0].replace("Row ", "")) - 1
            df_updated = df_existing.drop(index=row_idx_to_delete).reset_index(drop=True)

            if using_gsheets:
                conn.update(worksheet="Sheet1", data=df_updated)
                st.success("Entry removed permanently from Google Sheets!")
            else:
                st.session_state["entries"] = df_updated.to_dict("records")
                st.success("Entry removed temporarily!")
            st.rerun()
else:
    st.info("No entries logged yet. Extract details above and click 'Save & Log to Sheet'.")
