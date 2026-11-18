# ICFES CUN Snies Analyzer

Agente local de análisis de resultados ICFES (Saber TyT / Saber Pro) para la **Corporación Unificada Nacional de Educación Superior (CUN)**.

- Motor **100% local** (sin API keys de Google/OpenAI)
- Interfaz Streamlit con chat **Human-in-the-loop 50/50**
- Genera tablas, gráficas PNG, Word (`.docx`) y PDF

## Documentación

| Documento | Contenido |
| --- | --- |
| [COMO_EJECUTAR_EL_AGENTE.md](COMO_EJECUTAR_EL_AGENTE.md) | Guía paso a paso para ejecutar el agente |
| [INFORME_TECNICO.md](INFORME_TECNICO.md) | Arquitectura, datos, stack y operación |
| [snies-analyzer/README.md](snies-analyzer/README.md) | Resumen rápido del módulo de la app |

## Ejecución rápida

```bash
# Desde la raíz del repositorio
source .venv/Scripts/activate   # o: .venv\\Scripts\\Activate.ps1 en PowerShell
cd snies-analyzer
streamlit run app.py
```

Abrir: http://localhost:8501

## Estructura

```text
ICFES_CUN_Snies_Analyzer/
├── COMO_EJECUTAR_EL_AGENTE.md
├── INFORME_TECNICO.md
├── README.md
└── snies-analyzer/
    ├── app.py
    ├── cli_chat.py
    ├── requirements.txt
    ├── data_maestros/
    ├── data_muestra/
    └── src/
```

## Requisitos

- Python 3.11+
- Dependencias en `snies-analyzer/requirements.txt`
- Word o LibreOffice (opcional, para PDF)
