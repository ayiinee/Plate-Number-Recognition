import streamlit as st


def apply_custom_styles():
    st.markdown(
        """
        <style>
        .main-title {
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 0.25rem;
            color: #111827;
        }

        .subtitle {
            font-size: 0.95rem;
            color: #6B7280;
            margin-bottom: 1.5rem;
        }

        .section-card {
            background: #FFFFFF;
            padding: 1.25rem;
            border-radius: 16px;
            border: 1px solid #E5E7EB;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
            margin-bottom: 1rem;
        }

        .metric-label {
            color: #6B7280;
            font-size: 0.85rem;
        }

        .metric-value {
            color: #111827;
            font-size: 1.5rem;
            font-weight: 700;
        }

        div[data-testid="stSidebar"] {
            background-color: #FFFFFF;
            border-right: 1px solid #E5E7EB;
        }

        .stButton > button {
            border-radius: 10px;
            font-weight: 600;
        }

        .stDownloadButton > button {
            border-radius: 10px;
            font-weight: 600;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )