import streamlit as st


def render_dashboard():
    st.markdown('<div class="bloque-capigastos">', unsafe_allow_html=True)

    st.markdown(
        "<h2 style='color:#2B1E14;'>Dashboard</h2>",
        unsafe_allow_html=True
    )

    st.markdown(
        "Aquí irá el resumen general de tus gastos, gráficos y totales.",
        unsafe_allow_html=True
    )

    st.markdown('</div>', unsafe_allow_html=True)
