---
description: Reglas de negocio, esquemas CSV y arquitectura local de Snies Analyzer (CUN)
globs:
alwaysApply: true
---

# Snies Analyzer — Implementación Local (CUN)
Agente de análisis de resultados ICFES (Saber TyT y Saber Pro) por ciclos propedéuticos para la CUN.

## Reglas de Datos Inmutables
1. **Ejecución 100% local:** Sin API keys ni LLM de terceros. Narrativa determinística en `narrative_builder.py`. Salidas en `LOCAL_OUTPUT_DIR/[Sede]_[Programa]`.
2. **CSVs dinámicos (`;` o `,` + `utf-8-sig`):**
   - `promedio_puntaje_global.csv`: columnas `Año, SNIES, Media_Programa, Desv_Programa, Media_Institucion, Desv_Institucion, Media_Grupo_Referencia, Desv_Grupo_Referencia`.
   - `promedio_competencias_genericas.csv`: formato largo (`Snies` → `SNIES`). **Descartar siempre `Nivel de agregación == "Sede"`**. Conservar `Programa`, `Institución` y `Grupo de referencia NBC ***` (normalizar a `Grupo de referencia (NBC)`).
3. **Maestros estáticos en `data_maestros/`:**
   - `Medias_Nacionales_Puntaje_Global.csv` (sep `;`): limpiar `"Media "` → `"Media"`. Cruza por `Ciclo` (`Tecnico`, `Tecnologo`, `Profesional`) y `Año`.
   - `medias_agregados_competencias - Medias Nacionales TYT.csv` (sep `,`): ciclos Técnico/Tecnólogo.
   - `medias_agregados_competencias - Medias Nacionales Saber Pro.csv` (sep `,`): ciclo Profesional.
4. **Salidas:** 6 dimensiones x N ciclos confirmados = tablas (9 columnas) y gráficas de barras agrupadas (4 series).
