import re
import shutil
import unicodedata
from pathlib import Path

from src.chart_generator import generar_graficas_programa
from src.config import DIR_SALIDAS
from src.data_processor import procesar_tablas_programa
from src.narrative_builder import generar_narrativa_local
from src.report_builder import construir_word_y_pdf


def _limpiar_nombre(texto: str) -> str:
    """Nombre de carpeta/archivo seguro en Windows/OneDrive (sin tildes ni símbolos)."""
    nfkd = unicodedata.normalize("NFKD", texto.strip())
    sin_tildes = "".join(c for c in nfkd if not unicodedata.combining(c))
    limpio = re.sub(r'[\\/*?:"<>|]+', "_", sin_tildes)
    limpio = re.sub(r"\s+", "_", limpio)
    limpio = re.sub(r"_+", "_", limpio).strip("_")
    return limpio or "programa"


def ejecutar_pipeline_local(
    nombre_programa: str,
    sede: str,
    mapeo_ciclos: dict,
    ruta_global: str,
    ruta_comp: str,
) -> dict:
    carpeta_prog = _limpiar_nombre(f"{sede}_{nombre_programa}")
    carpeta_destino = DIR_SALIDAS / carpeta_prog
    carpeta_graficas = carpeta_destino / "graficas_png"
    carpeta_destino.mkdir(parents=True, exist_ok=True)

    # 1. Consolidar los 2 CSVs originales en la carpeta local del programa
    shutil.copy2(ruta_global, carpeta_destino / "promedio_puntaje_global.csv")
    shutil.copy2(ruta_comp, carpeta_destino / "promedio_competencias_genericas.csv")

    # 2. Tabulación de datos
    estructura = procesar_tablas_programa(nombre_programa, sede, ruta_global, ruta_comp, mapeo_ciclos)

    # 3. Generación de gráficas PNG
    total_graficas = generar_graficas_programa(estructura, carpeta_graficas)

    # Contar secciones con datos (p. ej. Resultados Globales)
    secciones_con_datos = {
        nom: list(ciclos.keys())
        for nom, ciclos in estructura.get("secciones", {}).items()
        if ciclos
    }
    if "Resultados Globales por Ciclo" not in secciones_con_datos:
        estructura.setdefault("alertas", []).append(
            "No se tabularon Resultados Globales: revise SNIES/mapeo y el CSV de puntaje global."
        )

    # 4. Narrativa determinística local (sin LLM / sin API keys)
    textos_ia = generar_narrativa_local(estructura)

    # 5. Construir Word y PDF locales (nombre ASCII)
    nombre_base = f"Informe_ICFES_{carpeta_prog}"
    salida_docs = construir_word_y_pdf(estructura, textos_ia, carpeta_destino, nombre_base)

    return {
        "estado": "completado" if salida_docs.get("ruta_docx") else "error",
        "carpeta_local": str(carpeta_destino.resolve()),
        "total_tablas_y_graficas": total_graficas,
        "secciones_generadas": secciones_con_datos,
        "ruta_docx": salida_docs["ruta_docx"],
        "ruta_pdf": salida_docs["ruta_pdf"],
        "aviso_pdf": salida_docs["aviso_pdf"],
        "alertas": estructura["alertas"],
        "motor_narrativa": textos_ia.get("motor_narrativa"),
    }
