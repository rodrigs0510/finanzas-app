import streamlit as st

def render_header():
    col1, col2 = st.columns([1, 5])

    with col1:
        st.image("assets/images/logo.png", width=160)

    with col2:
        st.markdown(
            "<h1 style='margin-top:30px; color:#4A3B2A;'>CAPIGASTOS</h1>",
            unsafe_allow_html=True
        )
