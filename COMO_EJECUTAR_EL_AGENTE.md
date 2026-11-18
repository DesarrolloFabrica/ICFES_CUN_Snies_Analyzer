# Cómo ejecutar Snies Analyzer (paso a paso)

Guía operativa para levantar el agente ICFES CUN en una próxima ocasión.  
Motor **100% local** · sin API keys · flujo **Human-in-the-loop 50/50**.

---

## 1. Requisitos previos

- Windows con PowerShell.
- Python 3.11+ (ya usado en el entorno del proyecto).
- Entorno virtual `.venv` en la raíz del repositorio.
- (Opcional) Microsoft Word o LibreOffice para generar el PDF automáticamente.

---

## 2. Abrir la carpeta del proyecto

Ruta del repositorio:

```text
C:\Users\diego_gutierrezo\OneDrive - Corporación Unificada Nacional de Educación Superior - CUN\Escritorio\ICFES_CUN_Snies_Analyzer
```

Abre esa carpeta en **Cursor** o en una terminal.

---

## 3. Activar el entorno virtual

En PowerShell, desde la **raíz** del repositorio:

```powershell
.\.venv\Scripts\Activate.ps1
```

Si PowerShell bloquea scripts, ejecuta una sola vez:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Verás el prefijo `(.venv)` en la terminal cuando esté activo.

---

## 4. Entrar a la carpeta del agente

```powershell
cd snies-analyzer
```

---

## 5. Iniciar el agente (Streamlit)

```powershell
streamlit run app.py
```

Si OneDrive da problemas con el hot-reload, usa:

```powershell
streamlit run app.py --server.fileWatcherType none
```

---

## 6. Abrir la interfaz

Cuando aparezca en la terminal:

```text
Local URL: http://localhost:8501
```

Abre el navegador en:

**http://localhost:8501**

---

## 7. Usar el agente (flujo HITL 50/50)

### 7.1 Cargar insumos (panel izquierdo)

1. Elige **Subir archivos** o **Leer desde carpeta local**.
2. Carga estos dos CSV:
   - `promedio_puntaje_global.csv`
   - `promedio_competencias_genericas.csv`
3. Espera el mensaje: **CSVs listos**.

> Prueba rápida con datos de ejemplo: carpeta `snies-analyzer/data_muestra`.

### 7.2 Conversar en el chat (confirma cada etapa)

1. Escribe el contexto, por ejemplo:  
   `programa: Administracion de Servicios de salud, sede: Bogota`
2. Confirma con **sí** (o usa los botones de atajo).
3. El agente inspecciona y propone el mapeo SNIES → confirma con **sí** (o corrige: `tecnico 14162, tecnologo …, profesional …`).
4. Confirma cobertura de ciclos (`sí, solo un ciclo` / `no, faltan`).
5. Confirma el alcance del informe (**Resultados Globales** + competencias).
6. Autoriza con **sí, generar**.

### 7.3 Recoger resultados

Al finalizar, el agente indica la carpeta de salida, normalmente:

```text
snies-analyzer\resultados_programas\[Sede]_[Programa]\
```

Allí encontrarás:

- Copia de los 2 CSV
- Carpeta `graficas_png/`
- Informe `.docx`
- Informe `.pdf` (si Word/LibreOffice está disponible)

---

## 8. Detener el agente

En la terminal donde corre Streamlit:

1. Enfoca esa ventana.
2. Presiona `Ctrl + C`.

---

## 9. Nueva sesión / otro programa

1. En la app, pulsa **Nueva sesión / Limpiar**.
2. Carga los CSV del nuevo programa.
3. Repite el flujo del chat (paso 7).

---

## 10. Alternativa por terminal (CLI)

Desde `snies-analyzer`, con el `.venv` activo:

```powershell
python cli_chat.py
```

Es el mismo cerebro del agente (HITL 50/50), en consola.  
Escribe `salir` para terminar.

---

## Resumen rápido (copiar / pegar)

```powershell
cd "C:\Users\diego_gutierrezo\OneDrive - Corporación Unificada Nacional de Educación Superior - CUN\Escritorio\ICFES_CUN_Snies_Analyzer"
.\.venv\Scripts\Activate.ps1
cd snies-analyzer
streamlit run app.py
```

Luego abre: **http://localhost:8501**

---

## Solución de problemas frecuentes

| Síntoma | Qué hacer |
| --- | --- |
| No abre `localhost:8501` | Verifica que Streamlit siga corriendo en la terminal. |
| Error de política de scripts | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| No genera PDF | Instala/usa Microsoft Word o LibreOffice; el `.docx` sí debe generarse. |
| Chat “viejo” o raro | Pulsa **Nueva sesión / Limpiar**. |
| Puerto ocupado | Cierra otras ventanas de Streamlit o usa `--server.port 8502`. |
