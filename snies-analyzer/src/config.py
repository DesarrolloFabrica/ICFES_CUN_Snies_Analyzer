import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DIR_MAESTROS = BASE_DIR / "data_maestros"
DIR_INPUTS_TEMP = BASE_DIR / "inputs_temp"

_output_env = os.getenv("LOCAL_OUTPUT_DIR", "./resultados_programas")
DIR_SALIDAS = Path(_output_env) if Path(_output_env).is_absolute() else (BASE_DIR / _output_env)

# Maestros nacionales (nombres reales en data_maestros/)
MAESTRO_GLOBAL = DIR_MAESTROS / "Medias_Nacionales_Puntaje_Global.csv"
MAESTRO_COMP_TYT = DIR_MAESTROS / "medias_agregados_competencias - Medias Nacionales TYT.csv"
MAESTRO_COMP_PRO = DIR_MAESTROS / "medias_agregados_competencias - Medias Nacionales Saber Pro.csv"

COMPETENCIAS = [
    ("Comunicación Escrita", "Comunicacion_Escrita", "comunicacion escrita"),
    ("Razonamiento Cuantitativo", "Razonamiento_Cuantitativo", "razonamiento cuantitativo"),
    ("Lectura Crítica", "Lectura_Critica", "lectura critica"),
    ("Competencias Ciudadanas", "Competencias_Ciudadanas", "competencias ciudadanas"),
    ("Inglés", "Ingles", "ingles"),
]

COLORES_SERIES = {
    "Programa": "#1B5E20",
    "Institución": "#4EA72E",
    "Grupo de referencia (NBC)": "#81C784",
    "Media nacional": "#455A64",
}

CICLOS_META = {
    "tecnico": ("TyT – Técnico", "TyT", "Tecnico"),
    "tecnologo": ("TyT – Tecnológico", "TyT", "Tecnologo"),
    "profesional": ("Saber Pro – Profesional", "Saber Pro", "Profesional"),
}
