import streamlit as st


def render_header():
    # CONTENEDOR PRINCIPAL
    st.markdown('<div class="bloque-capigastos">', unsafe_allow_html=True)

    # COLUMNAS GENERALES
    col_logo, col_filtros, col_kpi = st.columns([1.2, 2.5, 2.3])

    # =======================
    # LOGO + TITULO
    # =======================
    with col_logo:
        col_img, col_title = st.columns([1, 3])

        with col_img:
            st.image("assets/images/logo.png", width=150)

        with col_title:
            st.markdown(
                "<h1 style='margin-top: 25px; color:#2B1E14;'>Capigastos</h1>",
                unsafe_allow_html=True
            )

    # =======================
    # FILTROS
    # =======================
    with col_filtros:
        st.markdown("#### USUARIO")
        usuario = st.selectbox(
            "",
            ["Rodrigo", "Krys"],
            key="usuario_header"
        )

        c1, c2 = st.columns(2)

        with c1:
            st.markdown("#### MES")
            mes = st.selectbox(
                "",
                [
                    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
                ],
                key="mes_header"
            )

        with c2:
            st.markdown("#### AÑO")
            anio = st.number_input(
                "",
                min_value=2020,
                max_value=2100,
                value=2025,
                step=1,
                key="anio_header"
            )

    # =======================
    # KPI
    # =======================
    with col_kpi:
        st.markdown("""
        <div class="kpi-box">
            <div>SALDO TOTAL</div>
            <div style="font-size:22px; font-weight:900;">S/ 0.00</div>
        </div>
        <br>
        <div class="kpi-box">
            <div>AHORRO TOTAL</div>
            <div style="font-size:22px; font-weight:900; color:#2E8B57;">S/ 0.00</div>
        </div>
        """, unsafe_allow_html=True)

    # CIERRE DEL CONTENEDOR
    st.markdown('</div>', unsafe_allow_html=True)

