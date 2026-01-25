import streamlit as st

def render_registro():
    st.markdown("### Registro")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.selectbox(
            "Usuario",
            ["Juan", "María", "Pedro"]
        )

    with col2:
        st.selectbox(
            "Mes",
            ["Enero", "Febrero", "Marzo", "Abril"]
        )

    with col3:
        st.selectbox(
            "Año",
            ["2024", "2025"]
        )
