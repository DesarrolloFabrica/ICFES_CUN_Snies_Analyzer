from pathlib import Path
import shutil
import streamlit as st

from src.agent_core import crear_sesion_chat
from src.config import DIR_INPUTS_TEMP, DIR_SALIDAS
from src.data_processor import inspeccionar_csvs_programa
from src.pipeline import ejecutar_pipeline_local

st.set_page_config(page_title="Snies Analyzer | CUN", page_icon="📊", layout="wide")
st.title("📊 Snies Analyzer — Analista ICFES CUN")
st.caption(
    "Human-in-the-loop **50/50**: el chat confirma cada etapa contigo "
    "(insumos → contexto → SNIES → cobertura → alcance → generar). Motor 100% local · sin API keys."
)

DIR_INPUTS_TEMP.mkdir(parents=True, exist_ok=True)
RUTA_G_TEMP = DIR_INPUTS_TEMP / "promedio_puntaje_global.csv"
RUTA_C_TEMP = DIR_INPUTS_TEMP / "promedio_competencias_genericas.csv"


def inspeccionar_csvs() -> dict:
    if not (RUTA_G_TEMP.exists() and RUTA_C_TEMP.exists()):
        return {
            "ok": False,
            "error": "Faltan archivos CSV.",
            "alertas_10_porciento": ["Faltan archivos CSV en la sesión. Cárgalos en el panel izquierdo."],
            "snies_detectados": [],
        }
    return inspeccionar_csvs_programa(str(RUTA_G_TEMP), str(RUTA_C_TEMP))


def ejecutar_analisis_local(
    nombre_programa: str,
    sede: str,
    snies_tecnico: int = 0,
    snies_tecnologo: int = 0,
    snies_profesional: int = 0,
) -> dict:
    from src.config import CICLOS_META

    mapeo = {}
    if snies_tecnico:
        mapeo[int(snies_tecnico)] = CICLOS_META["tecnico"]
    if snies_tecnologo:
        mapeo[int(snies_tecnologo)] = CICLOS_META["tecnologo"]
    if snies_profesional:
        mapeo[int(snies_profesional)] = CICLOS_META["profesional"]

    if not mapeo:
        return {"estado": "error", "detalle": "Debes confirmar al menos un SNIES válido."}
    if not nombre_programa.strip() or not sede.strip():
        return {"estado": "error", "detalle": "Programa y sede son obligatorios."}
    if not (RUTA_G_TEMP.exists() and RUTA_C_TEMP.exists()):
        return {"estado": "error", "detalle": "Faltan los CSV de entrada en la sesión."}

    return ejecutar_pipeline_local(
        nombre_programa=nombre_programa.strip(),
        sede=sede.strip(),
        mapeo_ciclos=mapeo,
        ruta_global=str(RUTA_G_TEMP),
        ruta_comp=str(RUTA_C_TEMP),
    )


with st.sidebar:
    st.header("📁 Insumos")
    st.caption(f"Salida:\n`{DIR_SALIDAS.resolve()}`")

    modo = st.radio("¿Cómo cargar los 2 CSVs?", ["Subir archivos", "Leer desde carpeta local"])

    if modo == "Subir archivos":
        f_g = st.file_uploader("1. promedio_puntaje_global.csv", type=["csv"])
        f_c = st.file_uploader("2. promedio_competencias_genericas.csv", type=["csv"])
        if f_g:
            RUTA_G_TEMP.write_bytes(f_g.getbuffer())
        if f_c:
            RUTA_C_TEMP.write_bytes(f_c.getbuffer())
    else:
        carpeta_in = st.text_input(
            "Ruta de carpeta local con los 2 CSVs:",
            value=str((Path(__file__).parent / "data_muestra").resolve()),
        )
        if st.button("Cargar desde carpeta") and carpeta_in:
            p_in = Path(carpeta_in.strip())
            fg_local = p_in / "promedio_puntaje_global.csv"
            fc_local = p_in / "promedio_competencias_genericas.csv"
            if fg_local.exists() and fc_local.exists():
                shutil.copy2(fg_local, RUTA_G_TEMP)
                shutil.copy2(fc_local, RUTA_C_TEMP)
                st.success("✅ Archivos copiados.")
            else:
                st.error("No se encontraron ambos archivos en esa ruta.")

    if RUTA_G_TEMP.exists() and RUTA_C_TEMP.exists():
        st.success("✅ CSVs listos — sigue en el chat (50/50).")

    st.divider()
    st.subheader("Atajos de contexto")
    programa = st.text_input("Programa (también puedes decirlo en el chat)")
    sede = st.text_input("Sede (también puedes decirlo en el chat)")
    with st.expander("Override SNIES (opcional)"):
        snies_tec = st.number_input("SNIES TyT – Técnico", min_value=0, step=1, value=0)
        snies_teg = st.number_input("SNIES TyT – Tecnólogo", min_value=0, step=1, value=0)
        snies_pro = st.number_input("SNIES Saber Pro – Profesional", min_value=0, step=1, value=0)

    if st.button("🔄 Nueva sesión / Limpiar"):
        st.session_state.clear()
        st.rerun()


if "chat" not in st.session_state:
    st.session_state.chat = crear_sesion_chat([inspeccionar_csvs, ejecutar_analisis_local])
    st.session_state.mensajes = []
    saludo = st.session_state.chat.send_message("Hola")
    st.session_state.mensajes.append({"role": "assistant", "content": saludo.text})

st.session_state.chat.actualizar_contexto(
    programa=programa,
    sede=sede,
    snies_tecnico=int(snies_tec),
    snies_tecnologo=int(snies_teg),
    snies_profesional=int(snies_pro),
)

estado_actual = getattr(st.session_state.chat, "estado", "inicio")
st.info(f"Etapa actual del chat: `{estado_actual}` · confirma cada paso (HITL 50/50)")

for m in st.session_state.mensajes:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])


def _enviar_atajo(prompt_auto: str, con_spinner: bool = False) -> None:
    st.session_state.mensajes.append({"role": "user", "content": prompt_auto})
    if con_spinner:
        with st.spinner("Generando informe (mitad agente)..."):
            resp = st.session_state.chat.send_message(prompt_auto)
    else:
        resp = st.session_state.chat.send_message(prompt_auto)
    st.session_state.mensajes.append({"role": "assistant", "content": resp.text})
    if resp.meta:
        if "snies_detectados" in resp.meta:
            st.session_state["ultima_inspeccion"] = resp.meta
        if resp.meta.get("estado") == "completado":
            st.session_state["ultimo_resultado"] = resp.meta
    st.rerun()


c1, c2, c3, c4 = st.columns(4)
if c1.button("① Confirmar contexto"):
    _enviar_atajo("sí")
if c2.button("② Inspeccionar"):
    _enviar_atajo("inspeccionar")
if c3.button("③ Confirmar etapa"):
    prompt = "sí, solo un ciclo" if estado_actual == "confirmar_cobertura" else "sí"
    _enviar_atajo(prompt)
if c4.button("④ Sí, generar"):
    _enviar_atajo("sí, generar", con_spinner=True)

if prompt := st.chat_input("HITL 50/50 · Ej: programa: …, sede: … → sí → inspeccionar → sí → sí, generar"):
    st.session_state.mensajes.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Snies Analyzer (HITL 50/50)..."):
            respuesta = st.session_state.chat.send_message(prompt)
            st.markdown(respuesta.text)
    st.session_state.mensajes.append({"role": "assistant", "content": respuesta.text})
    if respuesta.meta:
        if "snies_detectados" in respuesta.meta:
            st.session_state["ultima_inspeccion"] = respuesta.meta
        if respuesta.meta.get("estado") == "completado":
            st.session_state["ultimo_resultado"] = respuesta.meta

if st.session_state.get("ultima_inspeccion"):
    with st.expander("Detalle inspección / mapeo propuesto", expanded=False):
        st.json(st.session_state["ultima_inspeccion"])

if st.session_state.get("ultimo_resultado"):
    with st.expander("Detalle último resultado", expanded=False):
        st.json(st.session_state["ultimo_resultado"])
