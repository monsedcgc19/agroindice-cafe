"""
ui.py — Componentes visuales compartidos entre las pantallas del dashboard
(no carga datos, ver data_loader.py para eso). Por ahora solo la tarjeta de
KPI usada en la pantalla de Resumen ejecutivo, pero pensada para
reutilizarse en las otras 2 pantallas del mockup.
"""

import streamlit as st

# Verde/rojo consistentes con la semántica de "bueno"/"malo" de cada delta,
# independientes del color de fondo de la tarjeta.
_DELTA_GOOD = {"bg": "#ecfdf3", "fg": "#067647"}
_DELTA_BAD = {"bg": "#fef3f2", "fg": "#b42318"}

# Íconos SVG en línea (sin CDN ni librería externa) en vez de emoji: el
# glifo de un emoji varía de alto según la fuente del sistema operativo del
# usuario, que fue justo la causa de la desalineación de tarjetas que se
# arregló antes -- un SVG con viewBox fijo siempre mide exactamente lo mismo.
# "warning", "check" y "pin" son los paths de Heroicons (MIT license,
# https://heroicons.com); "tree" es un ícono propio, sencillo.
_ICON_PATHS = {
    "warning": (
        '<path fill-rule="evenodd" clip-rule="evenodd" d="M9.401 3.003c1.155-2 4.043-2 5.197 0l7.355 '
        "12.748c1.154 2-.29 4.5-2.599 4.5H4.645c-2.309 0-3.752-2.5-2.598-4.5L9.4 3.003ZM12 8.25a.75.75 "
        "0 0 1 .75.75v3.75a.75.75 0 0 1-1.5 0V9a.75.75 0 0 1 .75-.75Zm0 8.25a.75.75 0 1 0 0-1.5.75.75 0 "
        '0 0 0 1.5Z"/>'
    ),
    "check": (
        '<path fill-rule="evenodd" clip-rule="evenodd" d="M2.25 12c0-5.385 4.365-9.75 9.75-9.75s9.75 '
        "4.365 9.75 9.75-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12Zm13.36-1.814a.75.75 0 1 0-1.22-.872l"
        '-3.236 4.53L9.53 12.22a.75.75 0 0 0-1.06 1.06l2.25 2.25a.75.75 0 0 0 1.14-.094l3.75-5.25Z"/>'
    ),
    "pin": (
        '<path fill-rule="evenodd" clip-rule="evenodd" d="M11.54 22.351l.07.04.028.016a.76.76 0 0 0 '
        ".723 0l.028-.015.071-.041a16.975 16.975 0 0 0 1.144-.742 19.58 19.58 0 0 0 2.683-2.282c1.944-"
        "1.99 3.963-4.98 3.963-8.827a8.25 8.25 0 0 0-16.5 0c0 3.846 2.02 6.837 3.963 8.827a19.58 19.58 "
        '0 0 0 2.682 2.282 16.975 16.975 0 0 0 1.145.742ZM12 13.5a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z"/>'
    ),
    "tree": '<path d="M12 2 7 10h2.5L6 17h4.9v4.5a1.1 1.1 0 0 0 2.2 0V17H18l-3.5-7H17L12 2Z"/>',
    "chart": (
        '<path d="M18.375 2.25c-1.035 0-1.875.84-1.875 1.875v15.75c0 1.035.84 1.875 1.875 1.875h.75c'
        "1.035 0 1.875-.84 1.875-1.875V4.125c0-1.036-.84-1.875-1.875-1.875h-.75ZM9.75 8.625c0-1.036."
        "84-1.875 1.875-1.875h.75c1.036 0 1.875.84 1.875 1.875v11.25c0 1.035-.84 1.875-1.875 1.875h-."
        "75a1.875 1.875 0 0 1-1.875-1.875V8.625ZM3 13.125c0-1.036.84-1.875 1.875-1.875h.75c1.036 0 1."
        '875.84 1.875 1.875v6.75c0 1.035-.84 1.875-1.875 1.875h-.75A1.875 1.875 0 0 1 3 19.875v-6.75Z"/>'
    ),
    "flag": (
        '<path fill-rule="evenodd" clip-rule="evenodd" d="M3 2.25a.75.75 0 0 1 .75.75v.54l1.838-.46a9'
        ".75 9.75 0 0 1 6.725.738l.108.054a8.25 8.25 0 0 0 5.58.652l3.109-.732a.75.75 0 0 1 .917.81 4"
        "7.784 47.784 0 0 0 .005 10.337.75.75 0 0 1-.574.812l-3.114.733a9.75 9.75 0 0 1-6.594-.77l-.1"
        '08-.054a8.25 8.25 0 0 0-5.69-.625l-2.202.55V21a.75.75 0 0 1-1.5 0V3A.75.75 0 0 1 3 2.25Z"/>'
    ),
    "bell": (
        '<path fill-rule="evenodd" clip-rule="evenodd" d="M5.25 9a6.75 6.75 0 0 1 13.5 0v.75c0 2.123.'
        "8 4.057 2.118 5.52a.75.75 0 0 1-.297 1.206c-1.544.57-3.16.99-4.831 1.243a3.75 3.75 0 1 1-7.4"
        "8 0 24.585 24.585 0 0 1-4.831-1.244.75.75 0 0 1-.298-1.205A8.217 8.217 0 0 0 5.25 9.75V9Zm4.5"
        '02 8.9a2.25 2.25 0 1 0 4.496 0 25.057 25.057 0 0 1-4.496 0Z"/>'
    ),
    "clock": (
        '<path fill-rule="evenodd" clip-rule="evenodd" d="M12 2.25c-5.385 0-9.75 4.365-9.75 9.75s4.36'
        "5 9.75 9.75 9.75 9.75-4.365 9.75-9.75S17.385 2.25 12 2.25ZM12.75 6a.75.75 0 0 0-1.5 0v6c0 .4"
        '14.336.75.75.75h4.5a.75.75 0 0 0 0-1.5h-3.75V6Z"/>'
    ),
}


def icon_svg(name, color, size=28, margin_bottom=16):
    """Ícono SVG en línea listo para insertar en el HTML de una tarjeta.
    `name` es una clave de _ICON_PATHS ("warning", "check", "pin", "tree").

    El margen va en el propio <svg> (no en un <div> que lo envuelva): un
    elemento reemplazado como <svg> respeta su width/height al pixel, sin
    las rarezas de caja de línea que sí afectan a un div flex contenedor.

    `flex-shrink:0` es necesario porque la tarjeta que lo contiene tiene una
    altura fija (`height`, no `min-height`, ver render_kpi_card) -- sin esto,
    una tarjeta con más contenido total (p. ej. con delta_text) encoge TODOS
    sus hijos flex, incluido el ícono, de forma desigual entre tarjetas."""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="{size}" height="{size}" '
        f'fill="{color}" style="display:block; flex-shrink:0; margin-bottom:{margin_bottom}px;">{_ICON_PATHS[name]}</svg>'
    )


def configure_page(title):
    """Layout ancho para las 3 pantallas del dashboard -- debe ser el primer
    comando de Streamlit que corre cada script de página (restricción de
    st.set_page_config), así que se llama antes que cualquier otro st.*."""
    st.set_page_config(page_title=title, layout="wide")


def style_narrow_selectbox(max_width=280):
    """Angosta cualquier st.selectbox de la página (por defecto ocupa todo
    el ancho del layout wide) y le da fondo blanco + borde gris redondeado,
    a juego con las tarjetas de KPI. Se puede llamar una sola vez por
    página -- el estilo aplica a TODOS los selectbox de esa página."""
    st.markdown(
        f"""
        <style>
        [data-testid="stSelectbox"] {{ max-width: {max_width}px; }}
        [data-testid="stSelectbox"] div[role="group"] {{
            background-color: #ffffff !important;
            border: 1px solid #d0d5dd !important;
            border-radius: 10px !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _one_line(html):
    """Streamlit/markdown trata cualquier línea indentada con 4+ espacios
    como bloque de código -- colapsar todo a una sola línea evita que un
    </div> anidado se escape y aparezca como texto literal."""
    return " ".join(line.strip() for line in html.splitlines() if line.strip())


def render_kpi_card(col, *, icon, label, value, bg_color, border_color, delta_text=None, delta_good=None, height=180):
    """Tarjeta de KPI con ícono, fondo de color, bordes redondeados y un
    badge de delta opcional (verde si delta_good=True, rojo si False). La
    flecha del badge se infiere del signo de `delta_text` (debe empezar con
    "+" o "-").

    `height` (px) es una altura fija, no un mínimo -- así todas las tarjetas
    de una misma fila quedan exactamente iguales sin importar si tienen o no
    delta_text. Si algún llamador necesita más espacio (p. ej. valores más
    largos en otra pantalla), puede subir este número.

    col: columna de Streamlit (de st.columns) donde se dibuja la tarjeta.
    """
    delta_html = ""
    if delta_text is not None:
        style = _DELTA_GOOD if delta_good else _DELTA_BAD
        arrow = "↓" if delta_text.strip().startswith("-") else "↑"
        delta_html = _one_line(
            f"""
            <div style="display:inline-block; margin-top:10px; padding:3px 12px;
                        border-radius:999px; font-size:13px; font-weight:600;
                        background-color:{style['bg']}; color:{style['fg']};">
                {arrow} {delta_text}
            </div>
            """
        )

    # justify-content:flex-start (no space-between) es lo que importa acá:
    # con space-between, una tarjeta sin delta_html (bloque de contenido más
    # corto) queda anclada al fondo de la tarjeta y su título termina más
    # abajo que el de una tarjeta con delta -- por eso los títulos no
    # quedaban alineados. Con flex-start + un margen fijo bajo el ícono, el
    # título siempre arranca a la misma altura sin importar cuánto contenido
    # haya debajo.
    card_html = _one_line(
        f"""
        <div style="background-color:{bg_color}; border:1px solid {border_color};
                    border-radius:16px; padding:20px 18px; height:{height}px; box-sizing:border-box;
                    display:flex; flex-direction:column; justify-content:flex-start;">
            {icon}
            <div style="font-size:13px; color:#475467; font-weight:600; line-height:1.3;
                        min-height:34px; margin-bottom:6px;">
                {label}
            </div>
            <div style="font-size:22px; font-weight:700; color:#101828; line-height:1.25;
                        word-wrap:break-word;">
                {value}
            </div>
            {delta_html}
        </div>
        """
    )
    col.markdown(card_html, unsafe_allow_html=True)
