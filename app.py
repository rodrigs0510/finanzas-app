import streamlit as st
from layout.header import render_header
from layout.registro import render_registro
from layout.dashboard import render_dashboard

st.set_page_config(
    page_title="CAPIGASTOS",
    layout="wide",
    page_icon="🐹"
)

render_header()
render_registro()
render_dashboard()



