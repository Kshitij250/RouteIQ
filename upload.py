import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Upload | ESG Logistics",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

from utils.sidebar import render_sidebar
render_sidebar()



# =========================================================
# PAGE CONFIG
# =========================================================

# =========================================================
# CUSTOM CSS
# =========================================================

st.markdown("""
<style>

/* =========================================================
MAIN BACKGROUND
========================================================= */

.main {

    background:
    linear-gradient(
        135deg,
        #020617,
        #0F172A,
        #111827
    );
}

.block-container {

    padding-top: 2rem;
    padding-bottom: 2rem;
}

/* =========================================================
TEXT STYLING
========================================================= */

h1 {

    color: white;

    font-size: 52px;

    font-weight: 800;

    text-align: center;

    margin-bottom: 10px;
}

.hero-text {

    color: #CBD5E1;

    text-align: center;

    font-size: 20px;

    line-height: 1.8;

    margin-bottom: 45px;
}

/* =========================================================
UPLOAD CONTAINER
========================================================= */

.upload-container {

    background:
    rgba(17,24,39,0.92);

    padding: 40px;

    border-radius: 24px;

    border:
    2px dashed #10B981;

    box-shadow:
    0px 4px 22px rgba(0,0,0,0.45);

    text-align: center;

    margin-top: 20px;

    margin-bottom: 25px;
}

.upload-title {

    color: white;

    font-size: 30px;

    font-weight: 700;

    margin-bottom: 12px;
}

.upload-subtitle {

    color: #CBD5E1;

    font-size: 17px;

    line-height: 1.7;
}

/* =========================================================
FILE UPLOADER
========================================================= */

[data-testid="stFileUploader"] {

    background:
    rgba(17,24,39,0.92);

    border:
    2px dashed #10B981;

    padding: 25px;

    border-radius: 18px;

    color: white;

    box-shadow:
    0px 4px 18px rgba(0,0,0,0.35);
}

/* =========================================================
SUCCESS BOX
========================================================= */

.success-box {

    background:
    linear-gradient(
        90deg,
        #10B981,
        #059669
    );

    padding: 20px;

    border-radius: 16px;

    color: white;

    text-align: center;

    font-size: 18px;

    font-weight: 600;

    margin-top: 20px;

    box-shadow:
    0px 4px 18px rgba(0,0,0,0.35);
}

/* =========================================================
BUTTONS
========================================================= */

.stButton>button {

    background:
    linear-gradient(
        90deg,
        #10B981,
        #059669
    );

    color: white;

    border-radius: 14px;

    border: none;

    padding: 0.85rem 1.5rem;

    font-size: 16px;

    font-weight: 600;

    width: 100%;

    transition: 0.3s;
}

.stButton>button:hover {

    transform: translateY(-2px);

    box-shadow:
    0px 4px 16px rgba(16,185,129,0.35);
}

/* =========================================================
SIDEBAR
========================================================= */

[data-testid="stSidebar"] {

    background:
    linear-gradient(
        180deg,
        #020617,
        #0F172A,
        #111827
    );

    border-right:
    1px solid rgba(255,255,255,0.08);
}

[data-testid="stSidebarNav"] {

    padding-top: 20px;
}

[data-testid="stSidebarNav"] a {

    background:
    rgba(255,255,255,0.04);

    color: #E2E8F0 !important;

    border-radius: 14px;

    margin-bottom: 12px;

    padding: 14px;

    transition: 0.3s;

    border:
    1px solid rgba(255,255,255,0.05);

    font-size: 15px;

    font-weight: 500;
}

[data-testid="stSidebarNav"] a:hover {

    background:
    linear-gradient(
        90deg,
        rgba(16,185,129,0.25),
        rgba(5,150,105,0.25)
    );

    transform: translateX(4px);

    border:
    1px solid rgba(16,185,129,0.45);

    color: white !important;
}

[data-testid="stSidebarNav"] a[aria-current="page"] {

    background:
    linear-gradient(
        90deg,
        #10B981,
        #059669
    );

    color: white !important;

    font-weight: 700;

    border:
    1px solid rgba(255,255,255,0.08);

    box-shadow:
    0px 4px 16px rgba(16,185,129,0.35);
}

/* =========================================================
DATAFRAME
========================================================= */

[data-testid="stDataFrame"] {

    border-radius: 16px;

    overflow: hidden;

    border: 1px solid #374151;
}

/* =========================================================
REMOVE STREAMLIT BRANDING
========================================================= */

#MainMenu {
    visibility: hidden;
}

footer {
    visibility: hidden;
}

header {
    visibility: hidden;
}

</style>
""", unsafe_allow_html=True)

# =========================================================
# HERO SECTION
# =========================================================

st.markdown("""
<h1>
ESG Logistics Intelligence Platform
</h1>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero-text">

AI-powered sustainability analytics platform for
ESG intelligence, route optimization,
carbon emission tracking,
and logistics sustainability insights.

</div>
""", unsafe_allow_html=True)

# =========================================================
# UPLOAD SECTION
# =========================================================

st.markdown("""
<div class="upload-container">

<div class="upload-title">
Upload Logistics Dataset
</div>

<div class="upload-subtitle">

Upload ESG logistics datasets in:
CSV or Excel format
for sustainability intelligence analysis.

</div>

</div>
""", unsafe_allow_html=True)

# =========================================================
# FILE UPLOADER
# =========================================================

uploaded_file = st.file_uploader(
    "",
    type=["csv", "xlsx"]
)

# =========================================================
# PROCESS FILE
# =========================================================

if uploaded_file is not None:

    try:

        # CSV FILE
        if uploaded_file.name.endswith(".csv"):

            df = pd.read_csv(uploaded_file)

        # EXCEL FILE
        else:

            df = pd.read_excel(uploaded_file)

        # STORE DATAFRAME
        st.session_state["uploaded_df"] = df

        # STORE FILE NAME
        st.session_state["uploaded_filename"] = (
            uploaded_file.name
        )

        # SUCCESS MESSAGE
        st.markdown(f"""
        <div class="success-box">

        Dataset Uploaded Successfully

        <br><br>

        {uploaded_file.name}

        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # DATA PREVIEW
        st.subheader("Dataset Preview")

        st.dataframe(
            df.head(),
            use_container_width=True
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # ESG DASHBOARD BUTTON
        if st.button(
            "Open ESG Analysis Dashboard"
        ):

            st.switch_page(
                "pages/1_ESG_Analysis.py"
            )

    except Exception as e:

        st.error(
            f"Error reading file: {e}"
        )
