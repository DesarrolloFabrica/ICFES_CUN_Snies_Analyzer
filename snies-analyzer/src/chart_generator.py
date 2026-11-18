from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")  # Backend sin interfaz gráfica para estabilidad en Streamlit
import matplotlib.pyplot as plt
from src.config import COLORES_SERIES

def _graficar_barras(df_tabla, titulo: str, ruta_png: Path):
    series = ["Programa", "Institución", "Grupo de referencia (NBC)", "Media nacional"]
    anios = df_tabla["Año"].astype(str).tolist()
    x = np.arange(len(anios))
    ancho = 0.20

    fig, ax = plt.subplots(figsize=(9.8, 4.7), dpi=300)
    max_val = 0

    for i, s in enumerate(series):
        vals = df_tabla[s].fillna(0).astype(float).tolist()
        if vals:
            max_val = max(max_val, max(vals))
        offset = (i - 1.5) * ancho
        barras = ax.bar(
            x + offset, vals, ancho, label=s, color=COLORES_SERIES[s], edgecolor="white", linewidth=0.4
        )
        for b in barras:
            h = b.get_height()
            if h > 0:
                ax.annotate(
                    f"{int(round(h))}",
                    xy=(b.get_x() + b.get_width() / 2, h),
                    xytext=(0, 2),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontsize=7.2,
                    fontweight="bold" if s == "Programa" else "normal",
                )

    ax.set_title(titulo, fontsize=10.5, fontweight="bold", pad=12, color="#1F2937")
    ax.set_xticks(x)
    ax.set_xticklabels(anios, fontsize=9)
    ax.set_ylabel("Puntaje promedio", fontsize=9)
    ax.set_ylim(0, (max_val * 1.18) if max_val > 0 else 100)
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=4, fontsize=8.5)

    plt.tight_layout()
    plt.savefig(ruta_png, bbox_inches="tight")
    plt.close(fig)

def generar_graficas_programa(estructura: dict, carpeta_graficas: Path) -> int:
    carpeta_graficas.mkdir(parents=True, exist_ok=True)
    programa = estructura["programa"]
    total = 0

    for idx_sec, (nom_sec, ciclos_dict) in enumerate(estructura["secciones"].items(), start=1):
        prefijo = "Resultados globales" if "Globales" in nom_sec else nom_sec
        slug_sec = nom_sec.replace(" ", "_").replace("ó", "o").replace("í", "i").replace("é", "e")
        for nom_ciclo, datos in ciclos_dict.items():
            snies = datos["snies"]
            rango = datos["rango_anios"]
            titulo = f"{prefijo} – {programa} – {nom_ciclo} ({rango})"
            ruta_img = carpeta_graficas / f"{idx_sec:02d}_{slug_sec}_{snies}.png"
            _graficar_barras(datos["tabla_df"], titulo, ruta_img)
            datos["ruta_grafica"] = str(ruta_img)
            total += 1

    return total