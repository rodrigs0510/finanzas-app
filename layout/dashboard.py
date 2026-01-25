import streamlit as st

def render_dashboard():
    st.markdown("### Dashboard")

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            label="Saldo total",
            value="S/. 2,500"
        )

    with col2:
        st.metric(
            label="Ahorro total",
            value="S/. 800"
        )
