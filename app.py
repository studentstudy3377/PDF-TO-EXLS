import streamlit as st

# -------------------------------
# CONSTANTS
# -------------------------------
APP_TITLE = "KP Sanghvi"
APP_ICON = "https://kpsanghvi.com/wp-content/uploads/elementor/thumbs/kp-logo-l-1-ra4wu10y8udmdikjwyopdd9oovnzc0j2fiff236cvw.png"

HOME = "Home"

st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide")

from igi_pdf import run_igi_pdf
from hrd_pdf_file import hrd_pdf_file
from fancy_gia_pdf import fancy_gia_pdf
from round_gia_pdf import run_round_gia_pdf

# -------------------------------
# STYLES
# -------------------------------

st.markdown(
    """
    <style>

    #MainMenu, footer, header, [data-testid="stDecoration"] { 
        display: none; 
    }

    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}

    /* Hide unwanted Streamlit elements */
    #MainMenu, footer, header, [data-testid="stDecoration"] { 
        display: none; 
    }

    /* Global title styling for better visibility in both themes */
    .streamlit-expanderHeader, .stText, .stMarkdown, .stButton, .stRadio, .stCheckbox, .stFileUploader, .stTextInput {
        font-weight: bold;
        font-size: 20px;
    }

    /* Detect user system theme (light or dark) */
    /* Light theme styling */
    @media (prefers-color-scheme: light) {
        .stApp {
            background-color: #f2f2f2;
            color: #333;  /* Dark text on light background */
        }

        .stButton > button {
            background: #fff;
            color: #333;
            border: 1px solid #666;
        }

        .stButton > button:hover {
            background: #ddd;
            color: #000;
        }

        .center-logo img {
            filter: brightness(1);
            display: block;
            margin-left: auto;
            margin-right: auto;
            max-width: 100%; /* Prevent logo from stretching */
            height: auto;
        }

        .center-logo {
            background-color: #333; /* Dark background */
            color: #f2f2f2; /* Light text on dark background */
            padding: 10px;
            border-radius: 10px;
            max-width: 300px; /* Control the width of the logo box */
            margin-left: auto;
            margin-right: auto;
        }

        /* Add outline around text_input and selectbox fields */
        .stTextInput input {
            border: 1px solid #000000;  /* Dark border for light theme */
            border-radius: 7px;          /* Rounded corners */
            padding: 10px;               /* Padding for better appearance */
        }
        
        /* Focused state - change border color */
        .stTextInput input:focus {
            border: 1px solid #000000;  /* Darker border when focused */
        }
        .stSelectbox div[data-baseweb="select"] {
        border: 1px solid #000000; /* Dark border */
        border-radius: 7px;         /* Rounded corners */
        padding: 5px;               /* Padding for better appearance */
        }

    }

    /* Dark theme styling */
    @media (prefers-color-scheme: dark) {
        .stApp {
            background-color: #0b0b0b;
            color: #f2f2f2;  /* Light text on dark background */
        }

        .stButton > button {
            background: #222;
            color: #eee;
            border: 1px solid #666;
        }

        .stButton > button:hover {
            background: #333;
            color: #FFD700;
        }

        .center-logo img {
            filter: brightness(1) invert(0);
            display: block;
            margin-left: auto;
            margin-right: auto;
            max-width: 100%; /* Prevent logo from stretching */
            height: auto;
        }

        .center-logo {
            background-color: #444; /* Darker background */
            color: #f2f2f2; /* Light text on dark background */
            padding: 10px;
            border-radius: 10px;
            max-width: 300px; /* Control the width of the logo box */
            margin-left: auto;
            margin-right: auto;
        }

        .css-1uvdxpz {
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            border-radius: 8px;
        }

        /* Add outline around text_input and selectbox fields */
        .stTextInput input {
            border: 1px solid #f2f2f2;  /* Light border for dark theme */
            border-radius: 7px;          /* Rounded corners */
            padding: 10px;               /* Padding for better appearance */
        }
        
        /* Focused state - change border color */
        .stTextInput input:focus{
            border: 1px solid #f2f2f2;  /* Lighter border when focused */
        }
        .stSelectbox div[data-baseweb="select"] {
        border: 1px solid #f2f2f2; /* Dark border */
        border-radius: 7px;         /* Rounded corners */
        padding: 5px;               /* Padding for better appearance */
        }       
    }
    
    </style>
    """,
    unsafe_allow_html=True
)

# Display the logo in the center
st.markdown(
    f'<div class="center-logo"><img src="{APP_ICON}" width="180" alt="KP Sanghvi Logo"/></div>',
    unsafe_allow_html=True,
)

MODE_KEY = "mode"

def get_mode(default: str = HOME) -> str:
    # Prefer session state; seed once from URL if missing
    if MODE_KEY not in st.session_state:
        url_mode = st.query_params.get("mode", default)
        st.session_state[MODE_KEY] = url_mode
    return st.session_state[MODE_KEY]

def set_mode(new_mode: str | None):
    # Update session state
    st.session_state[MODE_KEY] = new_mode or HOME
    # Mirror to URL for shareability
    if new_mode is None or new_mode == HOME:
        for k in ("mode", "deal", "report"):
            try:
                st.query_params.pop(k)
            except KeyError:
                pass
    else:
        st.query_params["mode"] = new_mode

def set_qp_bulk(updates: dict):
    """Apply multiple query-param updates; remove keys where value is None."""
    for k, v in updates.items():
        if v is None:
            try:
                st.query_params.pop(k)
            except KeyError:
                pass
        else:
            st.query_params[k] = v

def home_page():
    mode = get_mode(HOME)
   
    # Top navigation / Home
    if mode != HOME:
        if st.button("🏠 Home", key="btn_home_top"):
            set_qp_bulk({"mode": HOME, "deal": None, "report": None})
            set_mode(HOME)
            st.rerun()
    else:
        col1, col2, col3, col4, col5, col6, col7,col8,col9 = st.columns(9)

        with col5:
            st.markdown("###### Certificate To Excel")
            if st.button("🧾 Round GIA PDF"):
                set_qp_bulk({"mode": "🧾 Round GIA PDF", "deal": None, "report": None})
                set_mode("🧾 Round GIA PDF")
                st.rerun()
            if st.button("🧾 Fancy GIA PDF"):
                set_qp_bulk({"mode": "🧾 Fancy GIA PDF", "deal": None, "report": None})
                set_mode("🧾 Fancy GIA PDF")
                st.rerun()
            if st.button("🧾 HRD PDF"):
                set_qp_bulk({"mode": "🧾 HRD PDF", "deal": None, "report": None})
                set_mode("🧾 HRD PDF")
                st.rerun()
            if st.button("🧾 IGI PDF"):
                set_qp_bulk({"mode": "🧾 IGI PDF", "deal": None, "report": None})
                set_mode("🧾 IGI PDF")
                st.rerun()

    if mode == HOME:
        st.markdown("")
    elif mode == "🧾 Round GIA PDF":
        run_round_gia_pdf()
    elif mode == "🧾 Fancy GIA PDF":
        fancy_gia_pdf()
    elif mode == "🧾 HRD PDF":
        hrd_pdf_file()
    elif mode == "🧾 IGI PDF":
        run_igi_pdf()
    else:
        st.warning("Unknown mode. Returning Home…")
        set_qp_bulk({"mode": HOME, "deal": None, "report": None})
        set_mode(HOME)
        st.rerun()

if __name__ == "__main__":
    home_page()
