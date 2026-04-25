import os
import re
import pandas as pd
import fitz  # PyMuPDF
import streamlit as st
from io import BytesIO

# Function to extract text from PDF
def extract_text_from_pdf(uploaded_file):
    # Read the uploaded file as a BytesIO stream
    pdf_file = BytesIO(uploaded_file.read())
    
    # Open the PDF from the BytesIO stream
    pdf_document = fitz.open(stream=pdf_file, filetype="pdf")
    text = ""
    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        text += page.get_text()
    return text

# Function to parse extracted text
def parse_data(text):
    # Normalize line breaks for consistent matching.
    text_clean = re.sub(r'\r\n', '\n', text)
    text_clean = re.sub(r'\n+', '\n', text_clean.strip())
    
    data = {}

    # Extract HRD Antwerp Report Number
    match_hrd = re.search(r"N°\s*(?:\*+)?\s*(\d+)", text_clean, re.IGNORECASE)
    data["Report No"] = match_hrd.group(1) if match_hrd else ""
    
    # Assign Lab directly.
    data["Lab"] = "HRD"
    
    # Define regex patterns for other fields.
    patterns = {
        "Colour Grade": r"^Colour Grade\s+(.+?)(?:\s+grading|\n)",
        "Report Date": r"^(\w+\s\d{2},\s\d{4})",
        "Shape": r"^Shape\s+(\w+)",
        "Carat Weight": r"^Carat \(weight\)\s+([\d\.]+)\s*ct",
        "Fluorescence": r"^Fluorescence\s+(\w+)", 
        "Clarity Grade": r"^Clarity Grade\s+(\w+)",
        "Cut": r"(?:Proportions\s*(?:[:\-]?)\s*(excellent|very good|good|fair|poor))|Cut\s+\(Prop\./Pol\./Symm\.\)\s+(?P<cut_grade>\w+)",
        "Polish": r"^Polish\s+(very good|excellent|good|fair|poor)",
        "Symmetry": r"^Symmetry\s+(very good|excellent|good|fair|poor)",
        "Measurements": r"^Measurements\s+([\d\.\s\-\wx]+mm)",
        "Girdle": r"^Girdle\s+([a-zA-Z\s]+?)\s+\d+\.?\d*\s*%\s*faceted",
        'Girdle %': r"^Girdle\s+\w+\s+([\d\.]+\s*%)",
        "Culet": r"^Culet\s+(\w+)",
        "Depth %": r"^Total Depth\s+([\d\.]+\s*%)",
        "Table %": r"^Table Width\s+([\d\.]+\s*%)",
        "Crown Height": r"^Crown Height\s+\(.*?\)\s+([\d\.]+\s*%)",
        "Crown Angle": r"^Crown Height\s+\(.*?\)\s+[\d\.]+\s*%\s*\(\s*([\d\.]+)",
        "Pavilion Depth": r"^Pavilion Depth\s+\(.*?\)\s+([\d\.]+\s*%)",
        "Pavilion Angle": r"^Pavilion Depth\s+\(.*?\)\s+[\d\.]+\s*%\s*\(\s*([\d\.]+)",
        "Length Halves Crown": r"^Length Halves Crown\s+([\d\.]+\s*%)",
        "Length Halves Pavilion": r"^Length Halves Pavilion\s+([\d\.]+\s*%)",
    }

    for field, pattern in patterns.items():
        match = re.search(pattern, text_clean, re.MULTILINE)
        if match:
            if field == "Cut":
                extracted_value = match.group(1) or match.groupdict().get("cut_grade", "")
                extracted_value = extracted_value.strip()
            else:
                extracted_value = match.group(1).strip()

            if field == "Colour Grade":
                bracket_match = re.search(r"\(\s*([A-Za-z-]+)\s*\)", extracted_value)
                extracted_value = bracket_match.group(1) if bracket_match else ""
            elif field == "Girdle":
                extracted_value = extracted_value.lower().strip()

            data[field] = extracted_value
        else:
            data[field] = ""

    return data

# Function to convert DataFrame to Excel and return as a downloadable link
def convert_df_to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name="HRD Data")
    output.seek(0)
    return output

# Streamlit App
def hrd_pdf_file():
    st.title("HRD  PDF ")
    with st.sidebar:
        # Upload PDF files
        uploaded_files = st.file_uploader("Upload PDF files", type="pdf", accept_multiple_files=True)
    
    if uploaded_files:
        all_data = []
        
        # Process each uploaded PDF file
        for uploaded_file in uploaded_files:
            text = extract_text_from_pdf(uploaded_file)
            data = parse_data(text)
            all_data.append(data)

        # Create a DataFrame with all extracted data
        df = pd.DataFrame(all_data)
        
        # Display extracted data in the app
        st.subheader("Data")
        st.dataframe(df)

        if st.button("Download File"):
            excel_data = convert_df_to_excel(df)
            st.download_button(
                data=excel_data,
                file_name="HRD PDF File.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

if __name__ == '__main__':
    hrd_pdf_file()
