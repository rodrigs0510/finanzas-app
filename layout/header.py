import streamlit as st


def render_header():
    with st.container():
        col_logo, col_filtros, col_kpi = st.columns([1.3, 3.5, 2.2])

        # LOGO + TITULO
        with col_logo:
            st.image("assets/images/logo.png", width=180)
            st.markdown("## Capigastos")

        # FILTROS
        with col_filtros:
            st.markdown("**Usuario**")
            st.selectbox("", ["Rodrigo", "Krys"], key="usuario")

            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Mes**")
                st.selectbox(
                    "",
                    [
                        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
                    ],
                    key="mes"
                )

            with c2:
                st.markdown("**Año**")
                st.number_input("", 2020, 2100, 2025, key="anio")

        # KPI
        with col_kpi:
            st.metric("Saldo total", "S/ 0.00")
            st.metric("Ahorro total", "S/ 0.00")

