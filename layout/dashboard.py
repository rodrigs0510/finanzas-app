import streamlit as st

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.selectbox("Mes", ["Enero", "Febrero", "Marzo"])

with col2:
    st.selectbox("Año", [2024, 2025])

with col3:
    st.metric("Saldo total", "S/ 2,500")

with col4:
    st.metric("Ahorro total", "S/ 800")
