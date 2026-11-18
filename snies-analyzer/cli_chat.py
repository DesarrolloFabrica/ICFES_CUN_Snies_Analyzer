"""Puente CLI para conversar con Snies Analyzer (mismo cerebro HITL 50/50 que Streamlit)."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.agent_core import crear_sesion_chat
from src.config import CICLOS_META, DIR_INPUTS_TEMP
from src.data_processor import inspeccionar_csvs_programa
from src.pipeline import ejecutar_pipeline_local

DIR_INPUTS_TEMP.mkdir(parents=True, exist_ok=True)
RUTA_G = DIR_INPUTS_TEMP / "promedio_puntaje_global.csv"
RUTA_C = DIR_INPUTS_TEMP / "promedio_competencias_genericas.csv"


def _ensure_sample() -> None:
    if RUTA_G.exists() and RUTA_C.exists():
        return
    sample = ROOT / "data_muestra"
    shutil.copy2(sample / "promedio_puntaje_global.csv", RUTA_G)
    shutil.copy2(sample / "promedio_competencias_genericas.csv", RUTA_C)
    print("(CSV de data_muestra cargados en inputs_temp)\n")


def inspeccionar_csvs() -> dict:
    if not (RUTA_G.exists() and RUTA_C.exists()):
        return {
            "ok": False,
            "alertas_10_porciento": ["Faltan CSV. Colócalos en inputs_temp/ o data_muestra/."],
            "snies_detectados": [],
        }
    return inspeccionar_csvs_programa(str(RUTA_G), str(RUTA_C))


def ejecutar_analisis_local(
    nombre_programa: str,
    sede: str,
    snies_tecnico: int = 0,
    snies_tecnologo: int = 0,
    snies_profesional: int = 0,
) -> dict:
    mapeo = {}
    if snies_tecnico:
        mapeo[int(snies_tecnico)] = CICLOS_META["tecnico"]
    if snies_tecnologo:
        mapeo[int(snies_tecnologo)] = CICLOS_META["tecnologo"]
    if snies_profesional:
        mapeo[int(snies_profesional)] = CICLOS_META["profesional"]
    if not mapeo:
        return {"estado": "error", "detalle": "Sin SNIES."}
    return ejecutar_pipeline_local(
        nombre_programa=nombre_programa,
        sede=sede,
        mapeo_ciclos=mapeo,
        ruta_global=str(RUTA_G),
        ruta_comp=str(RUTA_C),
    )


def main() -> None:
    _ensure_sample()
    chat = crear_sesion_chat([inspeccionar_csvs, ejecutar_analisis_local])
    print(chat.send_message("Hola").text)
    print("\n(Escribe salir para terminar)\n")
    while True:
        try:
            user = input("Tú> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user:
            continue
        if user.lower() in {"salir", "exit", "quit"}:
            break
        resp = chat.send_message(user)
        print(f"\nAgente>\n{resp.text}\n")


if __name__ == "__main__":
    main()
