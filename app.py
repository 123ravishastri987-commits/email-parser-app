import datetime
import re
import streamlit as st
from PIL import Image
import pytesseract

st.set_page_config(page_title="Email Intimation Parser", layout="wide")

def parse_email_text(raw_text: str) -> dict:
    # 1. Email ID
    email_match = re.search(
        r'Email\s*ID\s*:\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        raw_text,
        re.IGNORECASE,
    )
    if email_match:
        email_id = email_match.group(1).strip()
    else:
        fallback = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', raw_text)
        email_id = fallback[0] if fallback else ""

    # 2. Requester (Full Name after 'To')
    requester_match = re.search(r'To\s*:?\s*([A-Za-z]+(?:\s+[A-Za-z]+)+)', raw_text, re.IGNORECASE)
    requester = requester_match.group(1).strip() if requester_match else ""

    # 3. Display Name
    display_match = re.search(r'Display\s*Name\s*:\s*([^\n\r]+)', raw_text, re.IGNORECASE)
    display_name = display_match.group(1).strip() if display_match else ""

    # 4. Request Number
    request_match = re.search(r'##RE-\d+##', raw_text)
    request_number = request_match.group(0) if request_match else ""

    return {
        "email_id": email_id,
        "display_name": display_name,
        "request_number": request_number,
        "requester": requester,
    }

st.title("Upload Email Screenshot")

# Initialize session state so data doesn't wipe when typing
if "parsed_data" not in st.session_state:
    st.session_state["parsed_data"] = {
        "email_id": "", "display_name": "", "request_number": "", "requester": ""
    }

col1, col2 = st.columns(2)

with col1:
    st.subheader("Upload Screenshot")
    uploaded_file = st.file_uploader("Upload screenshot (PNG, JPG)", type=["png", "jpg", "jpeg"])

    if uploaded_file is not None:
        st.image(uploaded_file, caption="Uploaded Image", use_container_width=True)
        
        if st.button("Extract Data from Image", type="primary"):
            with st.spinner("Extracting text via OCR..."):
                try:
                    # Open image and extract text
                    image = Image.open(uploaded_file)
                    extracted_text = pytesseract.image_to_string(image)
                    
                    # Parse the text
                    st.session_state["parsed_data"] = parse_email_text(extracted_text)
                    st.success("Extraction Complete!")
                except Exception as e:
                    st.error(f"OCR Error: {e}")

with col2:
    st.subheader("Extracted Details & Manual Inputs")

    email_val = st.text_input("UPN / Email ID", value=st.session_state["parsed_data"]["email_id"])
    display_val = st.text_input("Display Name", value=st.session_state["parsed_data"]["display_name"])
    created_val = st.text_input("When Created", value=datetime.date.today().strftime("%Y/%m/%d"))
    req_num_val = st.text_input("Request Number", value=st.session_state["parsed_data"]["request_number"])
    requester_val = st.text_input("Requester", value=st.session_state["parsed_data"]["requester"])
    location_val = st.selectbox("Location", ["GGN", "DEL", "MUM", "OTH"])

    if st.button("Submit Details", type="primary"):
        st.success("Details Submitted Successfully!")