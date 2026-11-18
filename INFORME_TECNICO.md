# Informe Técnico del Proyecto: Snies Analyzer (CUN)

**Versión:** 3.0 (Arquitectura 100% Local — Sin API keys)  
**Fecha:** 17 de noviembre de 2026  
**Organización:** Corporación Unificada Nacional de Educación Superior (CUN)  
**Entorno de Desarrollo y Ejecución:** Cursor IDE + Python + Streamlit (motor local determinístico)

---

## 1. Resumen Ejecutivo

**Snies Analyzer** es un agente de automatización analítica diseñado para actuar como un **Analista de Datos Senior experto en pruebas de Estado ICFES (Saber TyT y Saber Pro)** para la **CUN**. Su propósito es estandarizar, automatizar y acelerar el procesamiento estadístico y la redacción de informes institucionales de resultados por programa académico y sede, respetando el modelo de formación por ciclos propedéuticos (**Técnico Profesional, Tecnólogo y Profesional Universitario**).

El sistema combina la precisión matemática determinística de **Python** (`pandas` y `matplotlib`) con un **agente conversacional local** (máquina de estados + formulario Human-in-the-loop) y un **motor de narrativa determinística** que redacta el informe a partir de brechas y tendencias calculadas. **No requiere API keys de Google, OpenAI ni ningún servicio de pago.**

---

## 2. Requerimientos del Sistema

### 2.1 Requerimientos Funcionales
1. **Activación e Interacción Inicial (*Human-in-the-loop*):**
   - Activarse ante cualquier saludo o mensaje inicial del usuario, presentándose formalmente como *Snies Analyzer*.
   - Solicitar los 2 archivos CSV dinámicos del programa, el nombre exacto del programa académico y la sede correspondiente.
2. **Validación de Ciclos Propedéuticos por SNIES:**
   - Inspeccionar automáticamente los códigos SNIES presentes en ambos CSVs y sus rangos históricos/puntajes orientativos.
   - Solicitar confirmación explícita al usuario sobre qué código SNIES corresponde a **TyT – Técnico**, **TyT – Tecnológico** y **Saber Pro – Profesional**.
3. **Modelo Human-in-the-loop 50% / 50%:**
   - **50% Agente:** Inspecciona CSV, propone mapeo SNIES, calcula tablas, genera gráficas y ensambla Word/PDF.
   - **50% Humano (chat):** Confirma cada etapa antes de avanzar: insumos → programa/sede → mapeo SNIES → cobertura de ciclos → alcance del informe → autorización de generación → revisión del entregable.
4. **Generación Multi-Dimensión según Modelo Referente:**
   - Replicar la estructura del modelo `modelo - analisis y visualizacion.xlsx`: **6 dimensiones** (*Resultados Globales + 5 Competencias Genéricas*) desagregadas por los ciclos confirmados (**hasta 18 tablas y 18 gráficas de barras agrupadas**).
5. **Consolidación Documental Local:**
   - Crear una carpeta por cada análisis (`[Sede]_[Programa]`) que contenga: copia de los 2 CSVs originales, las gráficas en PNG, el informe en **Word (`.docx`)** y su exportación en **PDF (`.pdf`)** cuando haya convertidor local disponible.

### 2.2 Requerimientos No Funcionales y de Entorno
- **IDE de Implementación:** Cursor (con reglas contextuales en `.cursor/rules/snies-analyzer.md`).
- **Almacenamiento:** 100% en sistema de archivos local (sin OAuth ni cloud APIs), con ruta configurable mediante `.env` (`LOCAL_OUTPUT_DIR`).
- **Cero dependencia de API keys:** Prohibido el uso de Gemini/OpenAI u otros LLM de terceros en la ruta crítica de producción institucional.
- **Cero Alucinaciones Numéricas:** Todas las cifras provienen de cálculos exactos en Python; la narrativa solo describe esas cifras.
- **Trazabilidad y Reproducibilidad:** Código modular, tipado, versionable en Git.

---

## 3. Arquitectura de la Solución

### 3.1 Diagrama de Flujo y Componentes

```text
+-----------------------------------------------------------------------+
|                INTERFAZ (app.py - Streamlit)                          |
|  - Carga de los 2 CSVs + formulario programa/sede/SNIES               |
|  - Chat local Human-in-the-loop 50/50 (6 etapas de confirmación)     |
+-----------------------------------+-----------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------+
|     AGENTE LOCAL (agent_core.py) + PIPELINE (pipeline.py)             |
|  - Máquina de estados / orquestación 90-10                            |
|  1) inspeccionar_csvs()                                               |
|  2) ejecutar_analisis_local(programa, sede, mapeo_snies)              |
+-----------------+---------------------------------+-------------------+
                  |                                 |
                  v                                 v
+---------------------------------+   +---------------------------------+
|   VALIDACIÓN HUMANA (50%)       |   |   EJECUCIÓN AGENTE (50%)        |
|   (data_processor.py)           |   |  1. Copia CSVs a carpeta local  |
|  - Valida columnas y SNIES      |   |  2. Construye tablas            |
|  - Cruza años vs data_maestros/ |   |  3. Renderiza gráficas PNG      |
|                                 |   |  4. Narrativa local (sin LLM)   |
|                                 |   |  5. Genera .docx y .pdf local   |
+---------------------------------+   +----------------+----------------+
                                                       |
                                                       v
                                      +---------------------------------+
                                      |   CARPETA LOCAL CONSOLIDADA     |
                                      |   resultados_programas/         |
                                      |    └── [Sede]_[Programa]/       |
                                      +---------------------------------+
```

### 3.2 Stack Tecnológico

| Capa | Tecnología / Librería | Propósito |
| :--- | :--- | :--- |
| **IDE & Asistencia IA** | Cursor IDE | Desarrollo modular y reglas de contexto. |
| **Lenguaje** | Python 3.11+ | Orquestación, cálculo y generación documental. |
| **Interfaz** | Streamlit (`>=1.38.0`) | Chat + formulario local. |
| **Agente** | `agent_core.py` (local) | Protocolo HITL 50/50 sin API keys. |
| **Narrativa** | `narrative_builder.py` | Redacción determinística por brechas/tendencias. |
| **Motor Estadístico** | `pandas`, `numpy` | ETL y cruce con maestros. |
| **Visualización** | `matplotlib` (Agg, 300 DPI) | Hasta 18 gráficas de barras agrupadas. |
| **Documental** | `python-docx`, `docx2pdf`, LibreOffice | `.docx` y conversión local a `.pdf`. |
| **Configuración** | `python-dotenv`, `pathlib` | Rutas y entorno. |

---

## 4. Ingeniería y Modelo de Datos

### 4.1 Inventario de Fuentes de Datos

| Tipo | Archivo | Separador | Función |
| :--- | :--- | :--- | :--- |
| **Dinámico** | `promedio_puntaje_global.csv` | `;` (o `,`) | Resultados Globales por Ciclo |
| **Dinámico** | `promedio_competencias_genericas.csv` | `;` (o `,`) | 5 Competencias Genéricas |
| **Maestro** | `Medias_Nacionales_Puntaje_Global.csv` | `;` | Media nacional / Desv. global por Ciclo-Año |
| **Maestro** | `medias_agregados_competencias - Medias Nacionales TYT.csv` | `,` | Medias nacionales TyT |
| **Maestro** | `medias_agregados_competencias - Medias Nacionales Saber Pro.csv` | `,` | Medias nacionales Saber Pro |

El lector `leer_csv_icfes()` detecta automáticamente `;` vs `,` y limpia BOM/espacios en encabezados.

### 4.2 Reglas de Limpieza y Transformación (ETL)
1. Saneamiento de encabezados (`utf-8-sig`, `.str.strip()`).
2. Descarte de filas con `Nivel de agregación == "Sede"` en competencias.
3. Normalización de `"Grupo de referencia NBC ***"` → `"Grupo de referencia (NBC)"`.
4. Pivoteo largo→ancho con `pivot_table(..., aggfunc="first")`.
5. Estructura unificada de tablas (9 columnas):  
   `Año | Programa | Desv. Prog | Institución | Desv. Inst | Grupo de referencia (NBC) | Desv. NBC | Media nacional | Desv. Nac`

---

## 5. Estructura del Software

```text
snies-analyzer/
├── .cursor/rules/snies-analyzer.md
├── data_maestros/                 # 3 CSVs maestros nacionales
├── data_muestra/                  # CSVs sintéticos para prueba local
├── inputs_temp/                   # Área temporal de sesión
├── resultados_programas/          # Salidas consolidadas
├── src/
│   ├── config.py
│   ├── data_processor.py
│   ├── chart_generator.py
│   ├── narrative_builder.py       # Narrativa local sin LLM
│   ├── report_builder.py
│   ├── pipeline.py
│   └── agent_core.py              # Agente local HITL 50/50
├── app.py
├── requirements.txt               # Sin google-genai
└── .env                           # Solo LOCAL_OUTPUT_DIR
```

### Conversión local `.docx` → `.pdf`
1. LibreOffice / soffice headless (si existe).
2. `docx2pdf` + Microsoft Word (Windows/macOS).
3. Si no hay convertidor: se conserva el `.docx` y se informa el aviso.

---

## 6. Seguridad, Privacidad y Gobernanza

1. **Ley 1581 de 2012:** Los CSV contienen indicadores agregados por SNIES/año; no hay PII.
2. **Sin secretos de API:** No se almacena ni se exige `GEMINI_API_KEY` ni equivalentes.
3. **Determinismo:** La narrativa se genera solo a partir de métricas precalculadas.

---

## 7. Operación Local

### 7.1 Requisitos
- Python 3.11+.
- Cursor IDE.
- Microsoft Word o LibreOffice (opcional, solo para PDF).
- **No se requiere API key de Google ni recursos de pago.**

### 7.2 Ejecución
Desde la raíz del repositorio:

```powershell
.\.venv\Scripts\Activate.ps1
cd snies-analyzer
streamlit run app.py
```

Abrir `http://localhost:8501`, cargar los CSV (o usar `data_muestra/`), completar programa/sede/SNIES e inspeccionar/ejecutar.

### 7.3 Prueba rápida con datos sintéticos
Carpeta: `snies-analyzer/data_muestra/`  
SNIES de ejemplo: Técnico `101001`, Tecnólogo `101002`, Profesional `202001`.

---

## 8. Riesgos, Mitigaciones y Roadmap

| Riesgo | Impacto | Mitigación |
| :--- | :--- | :--- |
| Años del programa sin fila en maestros | Medias nacionales `NaN` | Alerta 10% en inspección |
| Separadores `;` vs `,` en CSV ICFES | Fallo de lectura | Detección automática de separador |
| Equipo sin Word/LibreOffice | Sin PDF | Se entrega `.docx` íntegro |
| Restricción institucional de API keys | Bloqueo del agente LLM | Arquitectura v3.0 100% local |

### Roadmap
- **Fase 2:** Plantilla Word corporativa CUN.
- **Fase 3:** Exportación Excel réplica del modelo.
- **Fase 4:** Empaquetado Docker para despliegue interno (sin APIs externas).
