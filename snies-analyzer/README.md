# Snies Analyzer (CUN) — Local

Agente de análisis ICFES (Saber TyT / Saber Pro) **100% local**, sin API keys ni servicios de pago.

## Ejecutar

Desde la raíz del repositorio:

```powershell
.\.venv\Scripts\Activate.ps1
cd snies-analyzer
streamlit run app.py
```

Abrir: http://localhost:8501

## Prueba rápida

1. En el panel izquierdo elige **Leer desde carpeta local**.
2. Ruta: la carpeta `data_muestra` de este proyecto.
3. Programa: `Tecnologia en Sistemas` · Sede: `Bogota`
4. SNIES: Técnico `101001` · Tecnólogo `101002` · Profesional `202001`
5. **Inspeccionar CSV** → **Ejecutar análisis local**

Salida en `resultados_programas/[Sede]_[Programa]/`.
