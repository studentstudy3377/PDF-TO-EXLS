import os
import re
import pandas as pd
from datetime import datetime
from PyPDF2 import PdfReader
import streamlit as st
from io import BytesIO

# Function to extract text from PDF
def extract_text_from_pdf(pdf_file):
    text = ""
    try:
        reader = PdfReader(pdf_file)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
    return text

def extract_key_to_symbols_and_identification(text, flags=re.IGNORECASE):
    key_to_symbols_text = ""

    # Extract paragraph under "KEY TO SYMBOLS"
    match = re.search(r"KEY TO SYMBOLS\s+([\s\S]+?)(?=\n\s*\n|ADDITIONAL GRADING INFORMATION)", text, flags)
    if match:
        key_to_symbols_text = match.group(1).strip().replace("\n", " ")

    # Also get "Identification Features"
    ident = re.search(r"Identification Features\s*([A-Z ,]+)", text, flags)
    if ident:
        idents = ident.group(1).strip()
        if key_to_symbols_text:
            key_to_symbols_text += " | Identification Features: " + idents
        else:
            key_to_symbols_text = idents

    return key_to_symbols_text

def extract_culet_type(text):
    matches = re.findall(r"\b(Pointed|None|Very Small|Small|Medium|Large|Very Large|Extremely Large)\b", text, re.IGNORECASE)
    if matches:
        return matches[-1].strip().title()
    return ""

def assign_sorted_percentage_values(percents):
    try:
        # Remove the '%' and convert to float
        float_values = [(float(p.replace("%", "")), p) for p in percents]
        # Sort by numeric value in descending order
        sorted_values = sorted(float_values, key=lambda x: x[0], reverse=True)
        
        def format_val(val):
            return str(int(val)) if val.is_integer() else str(val)
        
        sorted_percents = [format_val(x[0]) for x in sorted_values]
        keys = ["Depth %", "Table %", "Pav Dp", "Crn Dp"]
        return dict(zip(keys, sorted_percents))
    except Exception as e:
        st.error(f"Error in assign_sorted_percentage_values: {e}")
        return {key: "" for key in ["Depth %", "Table %", "Pav Dp", "Crn Dp"]}

def assign_sorted_degree_values(degree_list):
    try:
        float_values = [(float(d.replace("°", "")), d) for d in degree_list]
        sorted_values = sorted(float_values, key=lambda x: x[0], reverse=True)

        def format_val(val):
            return str(int(val)) if val.is_integer() else str(val)

        sorted_degrees = [format_val(x[0]) for x in sorted_values]
        keys = ["Pav Ang", "Crn Ang"]
        return dict(zip(keys, sorted_degrees))
    except Exception as e:
        st.error(f"Error in assign_sorted_degree_values: {e}")
        return {key: "" for key in ["Pav Ang", "Crn Ang"]}

def extract_value_percentages(text):
    clean_text = re.sub(r"\([^)]*\)", "", text)
    clean_text = re.sub(r"\s+", " ", clean_text)

    percents = re.findall(r"\d{1,3}\.?\d*%", clean_text)

    result = {}
    if len(percents) >= 4:
        first_four = percents[:4]
        sorted_columns = assign_sorted_percentage_values(first_four)
        result.update(sorted_columns)
    return result

def extract_value_degree(text):
    clean_text = re.sub(r"\([^)]*\)", "", text)
    clean_text = re.sub(r"\s+", " ", clean_text)

    degrees = re.findall(r"\d{1,3}\.?\d*°", clean_text)

    result = {}
    if len(degrees) >= 2:
        first_two = degrees[:2]
        result.update(assign_sorted_degree_values(first_two))
    return result

def extract_girdle(text):
    text_clean = re.sub(r'\s+', ' ', text)
    match = re.search(r"([A-Za-z\s]+To\s+[A-Za-z\s]+)\s*\(Faceted\)", text_clean, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""

def extract_standard_fields(text):
    flags = re.IGNORECASE
    data = {}

    rn = re.search(r"IGI\s+Report\s+Number\s*[:\s]*([\d]+)", text, flags)
    data["IGI Report Number"] = rn.group(1) if rn else ""
    dt = re.search(r"([A-Za-z]+\s+\d{1,2},\s+\d{4})", text)
    data["Date"] = dt.group(1) if dt else ""

    shape = re.search(r"Shape\s+and\s+Cutting\s+Style\s+([A-Z ]+)", text, flags)
    if shape:
        shape_val = shape.group(1).strip()
        shape_val = shape_val.replace("BRILLIANT", "").strip()
        data["Shape and Cutting Style"] = shape_val
    else:
        data["Shape and Cutting Style"] = ""

    text_clean = re.sub(r'\s+', ' ', text.strip())
    match_meas = re.search(r'(?i)Measurements\s+([\d\.\sxX-]+m{1,2})(?=\s|$)', text_clean)
    data["Measurements"] = match_meas.group(1).strip() if match_meas else ""

    carat = re.search(r"Carat\s+Weight\s*[:\s]*([\d\.]+)", text, flags)
    data["Carat Weight"] = carat.group(1) if carat else ""
    color = re.search(r"Color\s+Grade\s*[:\s]*([A-Z])", text, flags)
    data["Color Grade"] = color.group(1) if color else ""
    clarity = re.search(r"Clarity\s+Grade\s*[:\s]*([A-Z0-9 ]+)", text, flags)
    data["Clarity Grade"] = clarity.group(1).strip() if clarity else ""
    cut = re.search(r"Cut\s+Grade\s*[:\s]*([A-Z ]+)", text, flags)
    data["Cut Grade"] = cut.group(1).strip() if cut else ""
    polish = re.search(r"Polish\s+([A-Z]+)", text, flags)
    data["Polish"] = polish.group(1).strip() if polish else ""
    symmetry = re.search(r"Symmetry\s+([A-Z]+)", text, flags)
    data["Symmetry"] = symmetry.group(1).strip() if symmetry else ""
    fluoro = re.search(r"Fluorescence\s+([A-Z ]+)", text, flags)
    data["Fluorescence"] = fluoro.group(1).strip() if fluoro else ""

    comments = re.search(r"Comments:\s*(.+)", text, flags)
    data["Comments"] = comments.group(1).strip() if comments else ""
    data["Lab"] = "IGI"
    data["Key To Symbols"] = extract_key_to_symbols_and_identification(text, flags)
    data["Culet Type"] = extract_culet_type(text)
    data["Girdle"] = extract_girdle(text)

    return data

def extract_diamond_data(text):
    data = extract_standard_fields(text)
    value_data = extract_value_percentages(text)
    value_data_degree = extract_value_degree(text)
    data.update(value_data_degree)
    data.update(value_data)
    return data

def run_igi_pdf():
    st.title("IGI PDF")


    with st.sidebar:
        # Upload multiple PDF files
        uploaded_files = st.file_uploader("Upload IGI PDF files", type="pdf", accept_multiple_files=True)

    if uploaded_files:
        all_data = []
        for uploaded_file in uploaded_files:
            # st.write(f"Processing {uploaded_file.name} ...")
            text = extract_text_from_pdf(uploaded_file)
            data = extract_diamond_data(text)
            all_data.append(data)

        df = pd.DataFrame(all_data)

        st.subheader("Extracted Data Preview")
        st.dataframe(df)

        # Allow the user to download the extracted data as an Excel file
            # Save the extracted data to an Excel file in memory
        output = BytesIO()
        df.to_excel(output, index=False)
        output.seek(0)

        st.download_button(
            label="Download Excel File",
            data=output,
            file_name=f"IGI PDF Excel {datetime.now().strftime('%d-%m-%Y')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

if __name__ == '__main__':
    run_igi_pdf()
