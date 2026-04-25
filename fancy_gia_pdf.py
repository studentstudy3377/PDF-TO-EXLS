import os
import re
import io
import fitz  # PyMuPDF
import numpy as np
import pandas as pd
from PIL import Image
import easyocr
import streamlit as st

# -------------------------------------------------------------------------
# 1) REGEX PATTERNS FOR GIA FIELDS
# -------------------------------------------------------------------------
COMPILED_PATTERNS = {
    "Report Number": re.compile(r"GIA Report Number.*?(\d+)", re.IGNORECASE),
    "Lab":  re.compile(r"Inscription\(s\).*?(GIA)", re.IGNORECASE),
    "Shape and Cutting Style": re.compile(r"Shape and Cutting Style.*?(Round Brilliant|\w+)", re.IGNORECASE),
    "Measurements": re.compile(r"Measurements.*?(\d+\.\d+\s*x\s*\d+\.\d+\s*x\s*\d+\.\d+)\s*mm", re.IGNORECASE),
    "Carat Weight": re.compile(r"Carat Weight.*?(\d+\.\d+)\s*carat", re.IGNORECASE),
    "Color Grade": re.compile(r"Color Grade.*?([A-Z])", re.IGNORECASE),
    "Clarity Grade": re.compile(r"Clarity Grade.*?((?:Internally Flawless)|VVS\d|VS\d|SI\d|I\d|IF|FL)", re.IGNORECASE),
    "Cut Grade": re.compile(r"Cut Grade.*?(Excellent|Very Good|Good|Fair|Poor)", re.IGNORECASE),
    "Polish": re.compile(r"Polish.*?(Excellent|Very Good|Good|Fair|Poor)", re.IGNORECASE),
    "Symmetry": re.compile(r"Symmetry.*?(Excellent|Very Good|Good|Fair|Poor)", re.IGNORECASE),
    "Fluorescence": re.compile(r"Fluorescence.*?(None|Faint|Medium|Strong|Very Strong)", re.IGNORECASE),
    "Report Date": re.compile(r"([A-Za-z]+\s\d{2},\s\d{4})", re.IGNORECASE),
    "Inscription(s)": re.compile(r"Inscription\(s\).*?(GIA\s\d+)", re.IGNORECASE),
    "Key to Symbols": re.compile(r"KEY TO SYMBOLS\*([\s\S]*?)(?=\* Red symbols|\Z)", re.IGNORECASE),
    "Comments": re.compile(r"(?:Comments:\s*)(.*?)(?=(?:\d{9}|KEY TO SYMBOLS|\Z))", re.IGNORECASE | re.DOTALL),
    "Clarity Characteristics": re.compile(r"Clarity Characteristics.*?([A-Za-z,\s\-]+(?:\n[A-Za-z,\s\-]+)*)", re.IGNORECASE),
}

# -------------------------------------------------------------------------
# 2) UNWANTED CHUNKS
# -------------------------------------------------------------------------
UNWANTED_CHUNKS = [
    "GIA GA GIA COLOR CLARITY CUT SCALE S CALE SCALE FLAWLESS I INTERNALLY "
    "EXCELLENT FLAWLESS 1 2 1 VVS, 1 VERY 1 VVS2 600D 1 VS, N 4 VS 60 0D 1 SL, "
    "0 Sl2 FAIR 5 1 POOR",

    "3|a 31A 3|a Goi018 SLamTY ~UT SCALE SCaLE ScaLE F wUSS E E F EXCEMT' VTEHRTSUY G FawUSS 2 H E 3 3 #RY 3 K GQQ) 3 M 4 IV E 8 GOOD 4 5 R 1 6 2 Xax ] W 5 X 0 VOOK 2"
]

def remove_unwanted_chunks(text: str) -> str:
    for chunk in UNWANTED_CHUNKS:
        text = text.replace(chunk, "")
    text = re.sub(r"\s+", " ", text).strip()
    return text

# -------------------------------------------------------------------------
# 3) EXTRACT PDF TEXT & PARSE GIA DATA
# -------------------------------------------------------------------------
def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    all_text = []
    for page in doc:
        all_text.append(page.get_text())
    return "\n".join(all_text)

def parse_gia_data(text):
    data = {}
    clarity_chars_cleaned = ""

    for key, pattern in COMPILED_PATTERNS.items():
        if key not in ["Key to Symbols", "Clarity Characteristics"]:
            match = pattern.search(text)
            if match:
                if key == "Comments":
                    raw_comments = match.group(1)
                    cleaned = re.sub(r"\s+", " ", raw_comments).strip()
                    cleaned = re.sub(r"\*{2,}\d+", "", cleaned)
                    cleaned = re.sub(r"\b\d{9}\b", "", cleaned)
                    data[key] = cleaned.strip()
                else:
                    data[key] = match.group(1).strip()
            else:
                data[key] = ""

        elif key == "Clarity Characteristics":
            match = pattern.search(text)
            if match:
                raw_chars = match.group(1)
                cleaned = re.sub(r"\s+", " ", raw_chars).strip()

                parts = [part.strip() for part in cleaned.split(",")]
                filtered_parts = []
                for part in parts:
                    words = [w for w in part.split() if w.lower() != "inscription"]
                    if words:
                        filtered_parts.append(" ".join(words))
                clarity_chars_cleaned = " - ".join(filtered_parts)

    key_match = COMPILED_PATTERNS["Key to Symbols"].search(text)
    if key_match:
        content = key_match.group(1)
        lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
        data["Key to Symbols"] = " - ".join(lines)
    else:
        data["Key to Symbols"] = clarity_chars_cleaned

    return data

# -------------------------------------------------------------------------
# 4) EXTRACT IMAGES FROM PDF
# -------------------------------------------------------------------------
def extract_up_to_two_images(pdf_path, page_idx=0):
    doc = fitz.open(pdf_path)
    if page_idx >= len(doc):
        return []
    
    page = doc[page_idx]
    images_info = page.get_images(full=True)
    results = []

    for i, info in enumerate(images_info):
        if i > 1:  # only up to two images
            break
        xref = info[0]
        base_image = doc.extract_image(xref)
        img_bytes = base_image["image"]
        pil_img = Image.open(io.BytesIO(img_bytes))
        results.append(np.array(pil_img))
    
    return results

# -------------------------------------------------------------------------
# CLEANING OCR TEXT & SPLITTING
# -------------------------------------------------------------------------
def clean_ocr_token(token: str) -> str:
    token = re.sub(r'[()]+', '', token)
    token = re.sub(r'^[A-Za-z](?=\d)', '', token)
    token = re.sub(r'(?<=%)\d$', '', token)
    token = re.sub(r'[^0-9.%]', '', token)
    token = re.sub(r'(%\d+)$', '%', token)
    return token

def split_ocr_text_to_columns(ocr_text: str):
    text_cleaned = (
        ocr_text.replace(',.', '.')
                .replace('.,', '.')
                .replace('%/', '%')
    )
    raw_tokens = text_cleaned.split()
    
    numeric_tokens = []
    text_tokens = []
    
    mostly_numeric_pattern = re.compile(r"^[\d.,%]+$")
    
    for raw_token in raw_tokens:
        if mostly_numeric_pattern.match(raw_token):
            cleaned = clean_ocr_token(raw_token)
            numeric_tokens.append(cleaned)
        else:
            text_tokens.append(raw_token)

    return " ".join(numeric_tokens).strip(), " ".join(text_tokens).strip()

def remove_numbers_below_9(numbers_str: str) -> str:
    if not numbers_str:
        return numbers_str

    filtered_tokens = []
    for token in numbers_str.split():
        cleaned = token.rstrip('%')
        cleaned = re.sub(r'[^0-9\.]', '', cleaned)

        if cleaned.count('.') > 1 or not cleaned:
            continue

        try:
            val = float(cleaned)
            if val >= 9.0:
                filtered_tokens.append(token)
        except ValueError:
            pass

    return " ".join(filtered_tokens)

def parse_proportions_by_position(numbers_str: str):
    tokens = numbers_str.split()
    filtered = []
    for t in tokens:
        cleaned = re.sub(r'[^0-9\.]', '', t.strip().rstrip('%'))
        if cleaned.count('.') > 1:
            continue
        if cleaned:
            try:
                val = float(cleaned)
                if val >= 9:
                    filtered.append(t)
            except ValueError:
                pass

    def get_value(idx):
        if idx < len(filtered):
            orig = filtered[idx]
            try:
                numeric_val = float(orig.strip('%'))
                if idx in (3, 6):
                    truncated = int(numeric_val * 10) / 10.0
                    return f"{truncated:.1f}"
                else:
                    return orig
            except ValueError:
                return ""
        return ""

    return {
        "Table %": get_value(0),
        "Depth %": get_value(1),
    }

def format_token(token: str) -> str:
    suffix = '%' if token.endswith('%') else ''
    digits = re.sub(r'\D', '', token)
    if not digits:
        return token

    if len(digits) > 2:
        integer_part = digits[:2]
        decimal_digit = digits[2]
        formatted = f"{integer_part}.{decimal_digit}"
    else:
        formatted = f"{digits}.0"
    
    return formatted + suffix

def format_proportions_numbers(numbers_str: str) -> str:
    if not numbers_str:
        return numbers_str
    tokens = numbers_str.split()
    formatted_tokens = [format_token(t) for t in tokens]
    return " ".join(formatted_tokens)

def clean_proportions_text(txt: str) -> str:
    txt = re.sub(r"[|.%()]", " ", txt)
    allowed = {"extremely", "very", "slightly", "thin", "medium", "thick"}
    words = [w.lower() for w in txt.split() if w.lower() in allowed]
    cleaned = " ".join(words).title()
    return cleaned

def insert_dash_in_three_word_girdle(girdle_text: str) -> str:
    words = girdle_text.split()
    if len(words) == 3:
        words[0:2] = [f"{words[0]}-{words[1]}"]
    return " ".join(words).title().strip()

# Function to convert DataFrame to Excel and return as BytesIO
def get_excel_data(df):
    output = io.BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    return output

def process_pdf_files(uploaded_files):
    output_dir = "./output"
    os.makedirs(output_dir, exist_ok=True)
    all_data = []
    reader = easyocr.Reader(['en'], gpu=False)

    for idx, uploaded_file in enumerate(uploaded_files):
        # st.write(f"Processing: {uploaded_file.name}")
        pdf_path = os.path.join(output_dir, uploaded_file.name)
        with open(pdf_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        pdf_text = extract_text_from_pdf(pdf_path)
        pdf_text_cleaned = remove_unwanted_chunks(pdf_text)
        gia_data = parse_gia_data(pdf_text_cleaned)

        images = extract_up_to_two_images(pdf_path, page_idx=0)
        combined_ocr_parts = []
        for img_arr in images:
            ocr_result = reader.readtext(img_arr, detail=0)
            combined_ocr_parts.append(" ".join(ocr_result))
        full_ocr_text = " ".join(combined_ocr_parts).strip()

        if full_ocr_text:
            full_ocr_text = remove_unwanted_chunks(full_ocr_text)

        numbers_str, text_str = split_ocr_text_to_columns(full_ocr_text) if full_ocr_text else ("", "")
        numbers_str = remove_numbers_below_9(numbers_str)
        numbers_str = format_proportions_numbers(numbers_str)

        if numbers_str:
            proportions_map = parse_proportions_by_position(numbers_str)
            for k, v in proportions_map.items():
                if gia_data.get(k, "") == "" and v != "":
                    gia_data[k] = v

        text_str = clean_proportions_text(text_str)
        if text_str and 1 <= len(text_str.split()) <= 4:
            text_str = insert_dash_in_three_word_girdle(text_str)
            gia_data["Girdle"] = text_str
        else:
            gia_data["Girdle"] = ""

        gia_data["Girdle Condition"] = "Faceted"
        gia_data["Culet Size"] = "NON"

        girdle_percent_value = ""
        tokens = re.findall(r"[0-9.,%]+", full_ocr_text)
        for token in tokens:
            cleaned = token.replace(",", ".")
            cleaned = re.sub(r"[^\d.]", "", cleaned)
            if cleaned.count('.') > 1:
                continue
            try:
                val = float(cleaned)
                if val < 9.0:
                    girdle_percent_value = f"{val:.1f}%"
                    break
            except:
                continue

        gia_data["Girdle %"] = girdle_percent_value
        all_data.append(gia_data)

    df = pd.DataFrame(all_data)
    cols_to_clean = ["Table %", "Depth %", "Crn Ht", "Pav Dp"]
    for col in cols_to_clean:
        if col in df.columns:
            df[col] = df[col].str.replace('%', '', regex=False)

    return df

# Streamlit app structure
def fancy_gia_pdf():
    st.title("GIA Fancy PDF")
    st.sidebar.header("Upload PDF Files")

    uploaded_files = st.sidebar.file_uploader("Choose PDF files", accept_multiple_files=True, type=["pdf"])
    
    with st.spinner("Processing  ..."):
        if uploaded_files:
            st.write(f"Processing {len(uploaded_files)} PDF")

            try:
                result_df = process_pdf_files(uploaded_files)

                st.write("Processed Data:")
                st.dataframe(result_df)

                excel_data = get_excel_data(result_df)
                st.download_button(
                    label="Download Excel",
                    data=excel_data,
                    file_name="GIA_Fancy.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            
            except Exception as e:
                st.error(f"An error occurred while processing the PDFs: {str(e)}")
                print(f"Error: {str(e)}")

if __name__ == "__main__":
    fancy_gia_pdf()

