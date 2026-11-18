"""Generación determinística de narrativa analítica (sin LLM ni API keys)."""
from __future__ import annotations

from typing import Any


def _f(val: Any, nd: int = 1) -> str:
    try:
        if val is None:
            return "N/D"
        x = float(val)
        if x != x:  # NaN
            return "N/D"
        return f"{x:.{nd}f}"
    except (TypeError, ValueError):
        return "N/D"


def _tendencia(filas: list[dict]) -> tuple[str, float | None]:
    validos = [
        (int(r["Año"]), float(r["Programa"]))
        for r in filas
        if r.get("Programa") is not None and str(r.get("Programa")) not in ("", "nan")
    ]
    if len(validos) < 2:
        return "estable (serie corta)", None
    validos.sort(key=lambda t: t[0])
    delta = validos[-1][1] - validos[0][1]
    if delta > 2:
        return "ascendente", round(delta, 1)
    if delta < -2:
        return "descendente", round(delta, 1)
    return "estable", round(delta, 1)


def _brecha(ult: dict, col: str) -> float | None:
    try:
        prog = float(ult["Programa"])
        ref = float(ult[col])
        if prog != prog or ref != ref:
            return None
        return round(prog - ref, 1)
    except (TypeError, ValueError, KeyError):
        return None


def _frase_brecha(nombre: str, brecha: float | None) -> str:
    if brecha is None:
        return f"respecto a {nombre} no fue posible calcular la brecha (dato ausente)."
    if abs(brecha) < 0.5:
        return f"se ubica en paridad con {nombre} (brecha ≈ 0 puntos)."
    sentido = "por encima" if brecha > 0 else "por debajo"
    return f"se ubica {abs(brecha):.1f} puntos {sentido} de {nombre}."


def _analizar_ciclo(nom_sec: str, nom_ciclo: str, datos: dict) -> str:
    filas = datos.get("tabla") or []
    if not filas:
        return (
            f"Para {nom_sec} – {nom_ciclo} (SNIES {datos.get('snies', 'N/D')}) "
            "no hay filas tabuladas disponibles."
        )

    filas_ord = sorted(filas, key=lambda r: int(r["Año"]))
    primero, ultimo = filas_ord[0], filas_ord[-1]
    tend, delta = _tendencia(filas_ord)
    b_inst = _brecha(ultimo, "Institución")
    b_nbc = _brecha(ultimo, "Grupo de referencia (NBC)")
    b_nac = _brecha(ultimo, "Media nacional")

    desv = ultimo.get("Desv. Prog")
    rango = datos.get("rango_anios", "N/D")

    p1 = (
        f"En {nom_sec}, el ciclo {nom_ciclo} (SNIES {datos['snies']}, cohortes {rango}) "
        f"registra un promedio de programa de {_f(ultimo['Programa'])} en {ultimo['Año']} "
        f"(inicio de serie: {_f(primero['Programa'])} en {primero['Año']}). "
        f"La tendencia histórica es {tend}"
        + (f" con variación acumulada de {delta:+.1f} puntos." if delta is not None else ".")
    )

    p2 = (
        f"En el último año disponible, el programa {_frase_brecha('la Institución (CUN)', b_inst)} "
        f"Asimismo, {_frase_brecha('el Grupo de referencia (NBC)', b_nbc)} "
        f"Finalmente, {_frase_brecha('la Media nacional', b_nac)} "
        f"La desviación estándar del programa en ese año es {_f(desv)}, "
        "indicador de la dispersión interna de resultados."
    )
    return f"{p1}\n\n{p2}"


def _recomendaciones(estructura: dict) -> str:
    hallazgos: list[str] = []
    for nom_sec, ciclos in estructura.get("secciones", {}).items():
        for nom_ciclo, datos in ciclos.items():
            filas = datos.get("tabla") or []
            if not filas:
                continue
            ult = sorted(filas, key=lambda r: int(r["Año"]))[-1]
            b_nac = _brecha(ult, "Media nacional")
            if b_nac is not None and b_nac < -3:
                hallazgos.append(f"{nom_sec} / {nom_ciclo} (brecha nacional {b_nac:+.1f})")

    base = [
        "Fortalecer rutas de nivelación en las competencias con brecha negativa sostenida frente a la media nacional.",
        "Alinear el seguimiento académico por ciclo propedéutico (Técnico → Tecnólogo → Profesional) con metas de cierre de brecha NBC.",
        "Incorporar simulacros ICFES y retroalimentación por competencia en los semestres previos a la presentación de la prueba.",
        "Monitorear anualmente la desviación estándar del programa para detectar aumento de inequidad interna de aprendizajes.",
    ]
    if hallazgos:
        foco = "; ".join(hallazgos[:4])
        intro = (
            "La lectura transversal evidencia puntos de atención prioritaria en: "
            f"{foco}. "
        )
    else:
        intro = (
            "La lectura transversal no muestra brechas nacionales severas (< −3 puntos) "
            "en el último año; aun así, conviene sostener el ciclo de mejora continua. "
        )
    return intro + "Recomendaciones: 1) " + " 2) ".join(base)


def generar_narrativa_local(estructura: dict) -> dict:
    """Construye el JSON de textos del informe a partir de cifras ya calculadas."""
    programa = estructura.get("programa", "")
    sede = estructura.get("sede", "")
    ciclos_presentes = sorted(
        {
            ciclo
            for sec in estructura.get("secciones", {}).values()
            for ciclo in sec.keys()
        }
    )
    anios: set[int] = set()
    for sec in estructura.get("secciones", {}).values():
        for datos in sec.values():
            for fila in datos.get("tabla") or []:
                try:
                    anios.add(int(fila["Año"]))
                except (TypeError, ValueError, KeyError):
                    pass
    rango = f"{min(anios)}-{max(anios)}" if anios else "N/D"

    intro = (
        f"El presente informe consolida el análisis de resultados ICFES del programa "
        f"«{programa}» (Sede: {sede}) de la Corporación Unificada Nacional de Educación "
        f"Superior (CUN). Se examinan los ciclos propedéuticos presentes "
        f"({', '.join(ciclos_presentes) if ciclos_presentes else 'sin ciclos'}) "
        f"en el rango de cohortes {rango}. Todas las cifras provienen de cálculos "
        "determinísticos sobre los CSV del programa y las medias nacionales maestras; "
        "no se estiman ni se redondean de forma especulativa los indicadores tabulares."
    )

    analisis: dict[str, dict[str, str]] = {}
    for nom_sec, ciclos in estructura.get("secciones", {}).items():
        analisis[nom_sec] = {}
        for nom_ciclo, datos in ciclos.items():
            analisis[nom_sec][nom_ciclo] = _analizar_ciclo(nom_sec, nom_ciclo, datos)

    return {
        "introduccion_ejecutiva": intro,
        "analisis_por_seccion": analisis,
        "sintesis_y_recomendaciones": _recomendaciones(estructura),
        "motor_narrativa": "local_deterministico_v1",
    }
