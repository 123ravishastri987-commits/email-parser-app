import datetime
import re
import streamlit as st

# Set wide layout and title
st.set_page_config(page_title="User Budget & ID Tracker", layout="wide")


# Parsing logic
def parse_email_text(raw_text: str) -> dict:
    if not raw_text.strip():
        return {
            "email_id": "",
            "display_name": "",
            "request_number": "",
            "requester": "",
        }

    # 1. Extract UPN / Email ID
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

    # 2. Extract Requester (Full Name after 'To')
    requester_match = re.search(
        r'To\s*:?\s*([A-Za-z]+(?:\s+[A-Za-z]+)+)', raw_text, re.IGNORECASE
    )
    requester = requester_match.group(1).strip() if requester_match else ""

    # 3. Extract Display Name
    display_match = re.search(
        r'Display\s*Name\s*:\s*([^\n\r]+)', raw_text, re.IGNORECASE
    )
    display_name = display_match.group(1).strip() if display_match else ""

    # 4. Extract Request Number (e.g., ##RE-42661##)
    request_match = re.search(r'##RE-\d+##', raw_text)
    request_number = request_match.group(0) if request_match else ""

    return {
        "email_id": email_id,
        "display_name": display_name,
        "request_number": request_number,
        "requester": requester,
    }


# Header
st.title("Email Intimation Parser")
st.markdown("Paste the raw email content on the left to extract details.")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Paste Email Text")
    pasted_text = st.text_area(
        "Paste the complete email content here:",
        height=350,
        placeholder="Paste your email text here...",
    )

    # Automatically parse on paste/change
    parsed_data = parse_email_text(pasted_text)

with col2:
    st.subheader("Extracted Details & Manual Inputs")

    email_val = st.text_input(
        "UPN / Email ID",
        value=parsed_data["email_id"],
        key="email_input",
    )
    display_val = st.text_input(
        "Display Name",
        value=parsed_data["display_name"],
        key="display_input",
    )
    created_val = st.text_input(
        "When Created",
        value=datetime.date.today().strftime("%Y/%m/%d"),
        key="created_input",
    )
    req_num_val = st.text_input(
        "Request Number",
        value=parsed_data["request_number"],
        key="req_num_input",
    )
    requester_val = st.text_input(
        "Requester",
        value=parsed_data["requester"],
        key="requester_input",
    )
    location_val = st.selectbox("Location", ["GGN", "DEL", "MUM", "OTH"])

    if st.button("Submit Details", type="primary"):
        if email_val and requester_val:
            st.success("Details Submitted Successfully!")
        else:
            st.warning("Please paste email text or fill in required fields.")