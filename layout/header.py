import streamlit as st


def render_header():
    # CONTENEDOR PAPEL (BIEN HECHO)
    st.markdown('<div class="bloque-capigastos">', unsafe_allow_html=True)

    col_logo, col_filtros, col_kpi = st.columns([1.4, 3.6, 2.5])

    # ───────────────── LOGO + TITULO ─────────────────
    with col_logo:
        st.image("assets/images/logo.png", width=180)
        st.markdown(
            "<h2 style='margin-top:8px; color:#2B1E14;'>Capigastos</h2>",
            unsafe_allow_html=True
        )

    # ───────────────── FILTROS ─────────────────
    with col_filtros:
        st.markdown("<strong>Usuario</strong>", unsafe_allow_html=True)
        st.selectbox(
            "",
            ["Rodrigo", "Krys"],
            key="usuario_header"
        )

        c1, c2 = st.columns(2)

        with c1:
            st.markdown("<strong>Mes</strong>", unsafe_allow_html=True)
            st.selectbox(
                "",
                [
                    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
                ],
                key="mes_header"
            )

        with c2:
            st.markdown("<strong>Año</strong>", unsafe_allow_html=True)
            st.number_input(
                "",
                min_value=2020,
                max_value=2100,
                value=2025,
                step=1,
                key="anio_header"
            )

    # ───────────────── KPI ─────────────────
    with col_kpi:
        st.markdown("""
        <div class="kpi-box">
            <div>SALDO TOTAL</div>
            <div class="kpi-valor">S/ 0.00</div>
        </div>
        <br>
        <div class="kpi-box">
            <div>AHORRO TOTAL</div>
            <div class="kpi-valor verde">S/ 0.00</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
