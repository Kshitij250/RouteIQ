import streamlit as st

def render_sidebar():

    st.markdown("""
    <style>

    [data-testid="stSidebarNav"] { display: none !important; }

    [data-testid="stSidebar"] {
        background: #020617 !important;
        border-right: 1px solid rgba(255,255,255,0.06) !important;
    }

    [data-testid="stSidebar"] > div:first-child {
        padding: 0 !important;
    }

    .sidebar-brand-banner {
        background: linear-gradient(135deg, #022c22 0%, #064e3b 60%, #065f46 100%);
        padding: 22px 18px 18px;
        position: relative;
        overflow: hidden;
        margin-bottom: 6px;
    }

    .sidebar-brand-banner::before {
        content: '';
        position: absolute;
        top: -30px; right: -30px;
        width: 100px; height: 100px;
        border-radius: 50%;
        background: rgba(16,185,129,0.12);
    }

    .sidebar-brand-banner::after {
        content: '';
        position: absolute;
        bottom: -20px; left: -20px;
        width: 70px; height: 70px;
        border-radius: 50%;
        background: rgba(16,185,129,0.08);
    }

    .sidebar-logo-box {
        width: 42px; height: 42px;
        background: linear-gradient(135deg, #10B981, #059669);
        border-radius: 12px;
        display: flex; align-items: center; justify-content: center;
        font-size: 1.3rem;
        box-shadow: 0 4px 16px rgba(16,185,129,0.4);
        margin-bottom: 12px;
        position: relative; z-index: 1;
    }

    .sidebar-brand-title {
        color: #F0FDF4;
        font-size: 1rem;
        font-weight: 700;
        line-height: 1.2;
        position: relative; z-index: 1;
    }

    .sidebar-brand-sub {
        color: #6EE7B7;
        font-size: 0.7rem;
        font-weight: 500;
        margin-top: 2px;
        position: relative; z-index: 1;
    }

    .sidebar-status-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(16,185,129,0.15);
        border: 1px solid rgba(16,185,129,0.3);
        border-radius: 99px;
        padding: 4px 10px;
        margin-top: 10px;
        position: relative; z-index: 1;
    }

    .sidebar-pulse-dot {
        width: 6px; height: 6px;
        background: #10B981;
        border-radius: 50%;
        animation: esg-pulse 2s infinite;
    }

    .sidebar-status-txt {
        color: #6EE7B7;
        font-size: 0.68rem;
        font-weight: 600;
    }

    @keyframes esg-pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50%       { opacity: 0.4; transform: scale(0.8); }
    }

    .sidebar-section-lbl {
        color: #1E3A5F;
        font-size: 0.62rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        padding: 0 6px;
        margin-bottom: 8px;
        display: block;
    }

    [data-testid="stPageLink"] a {
        display: flex !important;
        align-items: center !important;
        gap: 10px !important;
        padding: 10px 12px !important;
        border-radius: 10px !important;
        margin-bottom: 4px !important;
        border: 1px solid transparent !important;
        background: transparent !important;
        color: #94A3B8 !important;
        font-size: 0.84rem !important;
        font-weight: 500 !important;
        text-decoration: none !important;
        transition: all 0.2s ease !important;
    }

    [data-testid="stPageLink"] a:hover {
        background: rgba(16,185,129,0.08) !important;
        border-color: rgba(16,185,129,0.25) !important;
        color: #E2E8F0 !important;
        transform: translateX(3px) !important;
    }

    [data-testid="stPageLink-active"] a {
        background: linear-gradient(135deg,
            rgba(16,185,129,0.18),
            rgba(5,150,105,0.15)) !important;
        border-color: rgba(16,185,129,0.45) !important;
        color: #10B981 !important;
        font-weight: 700 !important;
    }

    .sidebar-divider {
        height: 1px;
        background: linear-gradient(90deg,
            transparent,
            rgba(255,255,255,0.07),
            transparent);
        margin: 10px 14px;
    }

    .sidebar-dataset-card {
        background: rgba(255,255,255,0.02);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 12px;
        padding: 12px 14px;
        margin: 0 12px 12px;
    }

    .sidebar-dataset-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 10px;
    }

    .sidebar-dataset-icon {
        width: 26px; height: 26px;
        background: rgba(16,185,129,0.12);
        border-radius: 6px;
        display: flex; align-items: center;
        justify-content: center;
        font-size: 0.75rem;
    }

    .sidebar-dataset-title {
        color: #475569;
        font-size: 0.68rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    .sidebar-dataset-row {
        display: flex;
        justify-content: space-between;
        margin-bottom: 5px;
    }

    .sidebar-dataset-key { color: #334155; font-size: 0.7rem; }

    .sidebar-dataset-val {
        color: #10B981;
        font-size: 0.7rem;
        font-weight: 600;
        max-width: 110px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .sidebar-progress {
        height: 3px;
        background: rgba(255,255,255,0.05);
        border-radius: 99px;
        overflow: hidden;
        margin-top: 8px;
    }

    .sidebar-progress-fill {
        height: 100%;
        width: 100%;
        background: linear-gradient(90deg, #10B981, #059669);
        border-radius: 99px;
    }

    .sidebar-ready {
        color: #10B981;
        font-size: 0.65rem;
        font-weight: 600;
        margin-top: 5px;
    }

    .sidebar-no-data {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 6px 0;
    }

    .sidebar-no-dot {
        width: 8px; height: 8px;
        background: #EF4444;
        border-radius: 50%;
        flex-shrink: 0;
    }

    .sidebar-no-txt { color: #475569; font-size: 0.72rem; }

    .sidebar-no-hint {
        color: #334155;
        font-size: 0.68rem;
        margin-top: 4px;
        line-height: 1.5;
    }

    .sidebar-footer {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 16px 16px;
    }

    .sidebar-ver { color: #1E293B; font-size: 0.65rem; }

    .sidebar-beta {
        background: rgba(16,185,129,0.1);
        border: 1px solid rgba(16,185,129,0.2);
        border-radius: 99px;
        padding: 2px 8px;
        color: #059669;
        font-size: 0.62rem;
        font-weight: 700;
    }

    </style>
    """, unsafe_allow_html=True)

    with st.sidebar:

        # ── BRAND BANNER ──────────────────────────────────────
        st.markdown("""
        <div class="sidebar-brand-banner">
            <div class="sidebar-logo-box">🌿</div>
            <div class="sidebar-brand-title">ESG Platform</div>
            <div class="sidebar-brand-sub">Logistics Intelligence Suite</div>
            <div class="sidebar-status-pill">
                <div class="sidebar-pulse-dot"></div>
                <div class="sidebar-status-txt">System Online</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── NAV LABEL ─────────────────────────────────────────
        st.markdown(
            '<span class="sidebar-section-lbl">Navigation</span>',
            unsafe_allow_html=True
        )

        # ── PAGE LINKS ────────────────────────────────────────
        pages = [
            ("📤  Upload Dataset",        "upload.py"),
            ("📊  ESG Analysis",          "pages/1_ESG_Analysis.py"),
            ("🗺️  Route Optimization",    "pages/2_Route_Optimization.py"),
            ("🚗  Mobility Assistant",    "pages/3_Mobility_Assistant.py"),
        ]

        for label, path in pages:
            st.page_link(path, label=label, use_container_width=True)

        # ── DIVIDER ───────────────────────────────────────────
        st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

        # ── DATASET STATUS ────────────────────────────────────
        st.markdown(
            '<span class="sidebar-section-lbl">Dataset</span>',
            unsafe_allow_html=True
        )

        if ("uploaded_df" in st.session_state
                and st.session_state["uploaded_df"] is not None):

            df       = st.session_state["uploaded_df"]
            filename = st.session_state.get("uploaded_filename", "dataset.csv")
            rows, cols = df.shape

            st.markdown(f"""
            <div class="sidebar-dataset-card">
                <div class="sidebar-dataset-header">
                    <div class="sidebar-dataset-icon">📁</div>
                    <div class="sidebar-dataset-title">Loaded File</div>
                </div>
                <div class="sidebar-dataset-row">
                    <span class="sidebar-dataset-key">File</span>
                    <span class="sidebar-dataset-val"
                    title="{filename}">{filename}</span>
                </div>
                <div class="sidebar-dataset-row">
                    <span class="sidebar-dataset-key">Rows</span>
                    <span class="sidebar-dataset-val">{rows:,}</span>
                </div>
                <div class="sidebar-dataset-row">
                    <span class="sidebar-dataset-key">Columns</span>
                    <span class="sidebar-dataset-val">{cols}</span>
                </div>
                <div class="sidebar-progress">
                    <div class="sidebar-progress-fill"></div>
                </div>
                <div class="sidebar-ready">✓ Ready for analysis</div>
            </div>
            """, unsafe_allow_html=True)

        else:
            st.markdown("""
            <div class="sidebar-dataset-card">
                <div class="sidebar-dataset-header">
                    <div class="sidebar-dataset-icon">📁</div>
                    <div class="sidebar-dataset-title">Dataset</div>
                </div>
                <div class="sidebar-no-data">
                    <div class="sidebar-no-dot"></div>
                    <div class="sidebar-no-txt">No dataset uploaded</div>
                </div>
                <div class="sidebar-no-hint">
                    Upload a CSV or Excel file<br>from the Upload page.
                </div>
            </div>
            """, unsafe_allow_html=True)

        # ── DIVIDER ───────────────────────────────────────────
        st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

        # ── FOOTER ────────────────────────────────────────────
        st.markdown("""
        <div class="sidebar-footer">
            <div class="sidebar-ver">ESG Logistics v1.0</div>
            <div class="sidebar-beta">BETA</div>
        </div>
        """, unsafe_allow_html=True)