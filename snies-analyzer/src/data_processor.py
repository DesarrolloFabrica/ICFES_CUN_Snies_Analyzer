from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.config import (
    COMPETENCIAS,
    MAESTRO_COMP_PRO,
    MAESTRO_COMP_TYT,
    MAESTRO_GLOBAL,
)


def leer_csv_icfes(ruta) -> pd.DataFrame:
    """Lee CSV ICFES detectando separador (; o ,) y saneando encabezados."""
    path = Path(ruta)
    muestra = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()[:5]
    texto = "\n".join(muestra)
    sep = ";" if texto.count(";") >= texto.count(",") else ","
    df = pd.read_csv(path, sep=sep, encoding="utf-8-sig")
    df.columns = df.columns.str.strip()
    return df


def _normalizar_nivel(val: str) -> str:
    v = str(val).strip()
    return "Grupo de referencia (NBC)" if v.startswith("Grupo de referencia") else v


def _cargar_maestros():
    faltantes = [p.name for p in (MAESTRO_GLOBAL, MAESTRO_COMP_TYT, MAESTRO_COMP_PRO) if not p.exists()]
    if faltantes:
        raise FileNotFoundError(
            "Faltan archivos maestros en data_maestros/: " + ", ".join(faltantes)
        )

    df_nac_glob = leer_csv_icfes(MAESTRO_GLOBAL)
    df_nac_tyt = leer_csv_icfes(MAESTRO_COMP_TYT)
    df_nac_pro = leer_csv_icfes(MAESTRO_COMP_PRO)

    # Compatibilidad: columna "Media " residual o alias
    if "Media" not in df_nac_glob.columns:
        for c in list(df_nac_glob.columns):
            if c.lower().startswith("media"):
                df_nac_glob.rename(columns={c: "Media"}, inplace=True)
                break

    df_nac_glob["Ciclo"] = df_nac_glob["Ciclo"].astype(str).str.strip()
    df_nac_glob["Año"] = pd.to_numeric(df_nac_glob["Año"], errors="coerce")
    for d in (df_nac_tyt, df_nac_pro):
        d["Competencias"] = d["Competencias"].astype(str).str.strip().str.lower()
        d["Año"] = pd.to_numeric(d["Año"], errors="coerce")
    return df_nac_glob, df_nac_tyt, df_nac_pro


def inspeccionar_csvs_programa(ruta_global: str, ruta_comp: str) -> dict:
    """Inspecciona los 2 CSVs del programa y retorna SNIES, años y posibles alertas (10%)."""
    df_g = leer_csv_icfes(ruta_global)
    df_c = leer_csv_icfes(ruta_comp)
    if "Snies" in df_c.columns and "SNIES" not in df_c.columns:
        df_c.rename(columns={"Snies": "SNIES"}, inplace=True)

    alertas = []
    cols_g_req = {"Año", "SNIES", "Media_Programa", "Media_Institucion", "Media_Grupo_Referencia"}
    cols_c_req = {"Año", "SNIES", "Nivel de agregación", "Media_Comunicacion_Escrita"}

    if not cols_g_req.issubset(df_g.columns):
        alertas.append(f"Columnas faltantes en puntaje global: {sorted(cols_g_req - set(df_g.columns))}")
    if not cols_c_req.issubset(df_c.columns):
        alertas.append(f"Columnas faltantes en competencias: {sorted(cols_c_req - set(df_c.columns))}")
    if alertas:
        return {"ok": False, "alertas_10_porciento": alertas, "snies_detectados": []}

    snies_g = set(pd.to_numeric(df_g["SNIES"], errors="coerce").dropna().astype(int))
    snies_c = set(pd.to_numeric(df_c["SNIES"], errors="coerce").dropna().astype(int))

    if snies_g != snies_c:
        alertas.append(
            f"Los SNIES no coinciden entre archivos. Global: {sorted(snies_g)} vs Competencias: {sorted(snies_c)}"
        )

    try:
        df_nac_glob, _, _ = _cargar_maestros()
        anios_maestro = set(pd.to_numeric(df_nac_glob["Año"], errors="coerce").dropna().astype(int))
        anios_prog = set(pd.to_numeric(df_g["Año"], errors="coerce").dropna().astype(int)).union(
            set(pd.to_numeric(df_c["Año"], errors="coerce").dropna().astype(int))
        )
        anios_faltantes = sorted(anios_prog - anios_maestro)
        if anios_faltantes:
            alertas.append(
                f"Los años {anios_faltantes} aparecen en el CSV del programa pero no existen en los maestros nacionales."
            )
    except FileNotFoundError as e:
        alertas.append(str(e))

    detalle_snies = []
    df_g["_SNIES"] = pd.to_numeric(df_g["SNIES"], errors="coerce")
    for s in sorted(snies_g.union(snies_c)):
        sub = df_g[df_g["_SNIES"] == s]
        if not sub.empty:
            rango = f"{int(sub['Año'].min())}-{int(sub['Año'].max())}"
            prom = round(float(pd.to_numeric(sub["Media_Programa"], errors="coerce").mean()), 1)
            sugerencia = "Posible TyT (Técnico/Tecnólogo)" if prom < 125 else "Posible Saber Pro (Profesional)"
        else:
            rango, prom, sugerencia = "Sin datos globales", None, "Revisar"
        detalle_snies.append(
            {
                "snies": int(s),
                "rango_anios": rango,
                "puntaje_global_promedio": prom,
                "orientacion": sugerencia,
            }
        )

    return {
        "ok": True,
        "snies_detectados": detalle_snies,
        "alertas_10_porciento": alertas,
    }


def procesar_tablas_programa(
    nombre_programa: str,
    sede: str,
    ruta_global: str,
    ruta_comp: str,
    mapeo_ciclos: dict,
) -> dict:
    """Construye las tablas (Global + 5 Competencias x Ciclos) cruzadas con los 3 maestros."""
    df_global = leer_csv_icfes(ruta_global)
    df_comp = leer_csv_icfes(ruta_comp)
    if "Snies" in df_comp.columns and "SNIES" not in df_comp.columns:
        df_comp.rename(columns={"Snies": "SNIES"}, inplace=True)

    df_global["SNIES"] = pd.to_numeric(df_global["SNIES"], errors="coerce")
    df_global["Año"] = pd.to_numeric(df_global["Año"], errors="coerce")
    df_comp["SNIES"] = pd.to_numeric(df_comp["SNIES"], errors="coerce")
    df_comp["Año"] = pd.to_numeric(df_comp["Año"], errors="coerce")

    df_comp["Nivel_Norm"] = df_comp["Nivel de agregación"].apply(_normalizar_nivel)
    # Descartar explícitamente 'Sede'
    df_comp = df_comp[
        df_comp["Nivel_Norm"].isin(["Programa", "Institución", "Grupo de referencia (NBC)"])
    ].copy()

    df_nac_glob, df_nac_tyt, df_nac_pro = _cargar_maestros()
    estructura = {"programa": nombre_programa, "sede": sede, "secciones": {}, "alertas": []}

    # 1. RESULTADOS GLOBALES POR CICLO
    estructura["secciones"]["Resultados Globales por Ciclo"] = {}
    for snies, (nom_ciclo, _, clave_global) in mapeo_ciclos.items():
        sub = df_global[df_global["SNIES"] == snies].sort_values("Año")
        if sub.empty:
            estructura["alertas"].append(f"Sin datos globales para SNIES {snies} ({nom_ciclo}).")
            continue

        tabla = pd.DataFrame(
            {
                "Año": sub["Año"].astype(int),
                "Programa": pd.to_numeric(sub["Media_Programa"], errors="coerce"),
                "Desv. Prog": pd.to_numeric(sub["Desv_Programa"], errors="coerce"),
                "Institución": pd.to_numeric(sub["Media_Institucion"], errors="coerce"),
                "Desv. Inst": pd.to_numeric(sub["Desv_Institucion"], errors="coerce"),
                "Grupo de referencia (NBC)": pd.to_numeric(sub["Media_Grupo_Referencia"], errors="coerce"),
                "Desv. NBC": pd.to_numeric(sub["Desv_Grupo_Referencia"], errors="coerce"),
            }
        )
        nac_g = df_nac_glob[df_nac_glob["Ciclo"] == clave_global][["Año", "Media", "Desv"]].copy()
        nac_g["Año"] = nac_g["Año"].astype(int)
        tabla = tabla.merge(nac_g, on="Año", how="left")
        tabla.rename(columns={"Media": "Media nacional", "Desv": "Desv. Nac"}, inplace=True)

        estructura["secciones"]["Resultados Globales por Ciclo"][nom_ciclo] = {
            "snies": int(snies),
            "rango_anios": f"{int(tabla['Año'].min())}-{int(tabla['Año'].max())}",
            "tabla_df": tabla,
            "tabla": tabla.to_dict(orient="records"),
        }

    # 2. LAS 5 COMPETENCIAS GENÉRICAS
    cols_niveles = ["Programa", "Institución", "Grupo de referencia (NBC)"]
    for nom_comp, sufijo_col, clave_nac in COMPETENCIAS:
        estructura["secciones"][nom_comp] = {}
        for snies, (nom_ciclo, tipo_prueba, _) in mapeo_ciclos.items():
            sub = df_comp[df_comp["SNIES"] == snies].copy()
            if sub.empty:
                estructura["alertas"].append(f"Sin datos de {nom_comp} para SNIES {snies} ({nom_ciclo}).")
                continue

            col_m = f"Media_{sufijo_col}"
            col_d = f"Desv_{sufijo_col}"
            if col_m not in sub.columns:
                estructura["alertas"].append(f"Columna ausente {col_m} para {nom_comp}.")
                continue

            piv_m = (
                sub.pivot_table(index="Año", columns="Nivel_Norm", values=col_m, aggfunc="first")
                .reindex(columns=cols_niveles)
            )
            piv_d = (
                sub.pivot_table(index="Año", columns="Nivel_Norm", values=col_d, aggfunc="first")
                .reindex(columns=cols_niveles)
            )

            tabla = pd.DataFrame(
                {
                    "Año": piv_m.index.astype(int),
                    "Programa": piv_m["Programa"].values,
                    "Desv. Prog": piv_d["Programa"].values,
                    "Institución": piv_m["Institución"].values,
                    "Desv. Inst": piv_d["Institución"].values,
                    "Grupo de referencia (NBC)": piv_m["Grupo de referencia (NBC)"].values,
                    "Desv. NBC": piv_d["Grupo de referencia (NBC)"].values,
                }
            ).sort_values("Año")

            df_nac_ref = df_nac_tyt if tipo_prueba == "TyT" else df_nac_pro
            nac_c = df_nac_ref[df_nac_ref["Competencias"] == clave_nac][
                ["Año", "Media_Nacional", "Desv_Nacional"]
            ].copy()
            nac_c["Año"] = nac_c["Año"].astype(int)
            tabla = tabla.merge(nac_c, on="Año", how="left")
            tabla.rename(
                columns={"Media_Nacional": "Media nacional", "Desv_Nacional": "Desv. Nac"},
                inplace=True,
            )

            estructura["secciones"][nom_comp][nom_ciclo] = {
                "snies": int(snies),
                "rango_anios": f"{int(tabla['Año'].min())}-{int(tabla['Año'].max())}",
                "tabla_df": tabla,
                "tabla": tabla.to_dict(orient="records"),
            }

    return estructura
