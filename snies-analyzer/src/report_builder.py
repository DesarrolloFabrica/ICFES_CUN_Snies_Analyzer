import platform
import shutil
import subprocess
import tempfile
import unicodedata
from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
from docx.shared import Inches, Pt, RGBColor


def _colorear_celda(cell, hex_color: str):
    shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    cell._tc.get_or_add_tcPr().append(shading)


def _ascii_seguro(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _convertir_a_pdf_local(ruta_docx: Path, carpeta_destino: Path) -> tuple[str | None, str | None]:
    """Convierte DOCX→PDF evitando fallos de Word/COM con tildes y rutas OneDrive."""
    ruta_pdf = ruta_docx.with_suffix(".pdf")
    errores: list[str] = []

    # 1. LibreOffice
    cmd = shutil.which("libreoffice") or shutil.which("soffice")
    if cmd:
        try:
            subprocess.run(
                [cmd, "--headless", "--convert-to", "pdf", str(ruta_docx), "--outdir", str(carpeta_destino)],
                check=True,
                capture_output=True,
                text=True,
            )
            if ruta_pdf.exists():
                return str(ruta_pdf), None
            errores.append("LibreOffice no produjo el PDF esperado.")
        except Exception as e:
            errores.append(f"LibreOffice: {e}")

    if platform.system() not in ("Windows", "Darwin"):
        return None, "No se encontró convertidor PDF. " + " | ".join(errores)

    # 2. Word/COM vía carpeta temporal ASCII (sin tildes / fuera de OneDrive)
    tmp_root = Path(tempfile.gettempdir()) / "snies_analyzer_pdf"
    tmp_root.mkdir(parents=True, exist_ok=True)
    nombre_ascii = _ascii_seguro(ruta_docx.stem).replace(" ", "_")
    tmp_docx = tmp_root / f"{nombre_ascii}.docx"
    tmp_pdf = tmp_root / f"{nombre_ascii}.pdf"
    try:
        if tmp_docx.exists():
            tmp_docx.unlink()
        if tmp_pdf.exists():
            tmp_pdf.unlink()
        shutil.copy2(ruta_docx, tmp_docx)

        if platform.system() == "Windows":
            import pythoncom
            import win32com.client

            pythoncom.CoInitialize()
            word = None
            try:
                word = win32com.client.DispatchEx("Word.Application")
                word.Visible = False
                word.DisplayAlerts = 0
                doc = word.Documents.Open(str(tmp_docx), ReadOnly=True)
                # 17 = wdFormatPDF
                doc.SaveAs(str(tmp_pdf), FileFormat=17)
                doc.Close(False)
            finally:
                if word is not None:
                    word.Quit()
        else:
            from docx2pdf import convert

            convert(str(tmp_docx), str(tmp_pdf))

        if tmp_pdf.exists() and tmp_pdf.stat().st_size > 0:
            shutil.copy2(tmp_pdf, ruta_pdf)
            return str(ruta_pdf), None
        errores.append("Word/COM no generó PDF en carpeta temporal.")
    except Exception as e:
        errores.append(f"Word/COM temp: {e}")
        # Fallback docx2pdf directo
        try:
            if platform.system() == "Windows":
                import pythoncom

                pythoncom.CoInitialize()
            from docx2pdf import convert

            convert(str(tmp_docx), str(tmp_pdf))
            if tmp_pdf.exists():
                shutil.copy2(tmp_pdf, ruta_pdf)
                return str(ruta_pdf), None
        except Exception as e2:
            errores.append(f"docx2pdf fallback: {e2}")
    finally:
        for p in (tmp_docx, tmp_pdf):
            try:
                if p.exists():
                    p.unlink()
            except OSError:
                pass

    return None, "Word generado, pero falló conversión a PDF. " + " | ".join(errores)


def construir_word_y_pdf(estructura: dict, textos_ia: dict, carpeta_destino: Path, nombre_base: str) -> dict:
    doc = Document()
    nombre_base = _ascii_seguro(nombre_base).replace(" ", "_")

    h0 = doc.add_heading("Informe de Análisis de Resultados ICFES\n(Saber TyT y Saber Pro)", level=0)
    h0.alignment = WD_ALIGN_PARAGRAPH.CENTER

    p_meta = doc.add_paragraph()
    p_meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_meta = p_meta.add_run(
        f"Programa Académico: {estructura['programa']}\n"
        f"Sede: {estructura['sede']}\n"
        "Corporación Unificada Nacional de Educación Superior (CUN)"
    )
    r_meta.bold = True

    doc.add_heading("1. Introducción Ejecutiva", level=1)
    doc.add_paragraph(textos_ia.get("introduccion_ejecutiva", ""))

    for num_sec, (nom_sec, ciclos_dict) in enumerate(estructura["secciones"].items(), start=2):
        doc.add_page_break()
        doc.add_heading(f"{num_sec}. {nom_sec}", level=1)

        if not ciclos_dict:
            doc.add_paragraph(
                "Sin ciclos tabulados en esta sección. Verifique el mapeo SNIES y los CSV de entrada."
            )
            continue

        for nom_ciclo, datos in ciclos_dict.items():
            doc.add_heading(f"{nom_ciclo} (SNIES {datos['snies']})", level=2)

            registros = datos.get("tabla") or []
            if registros:
                columnas = list(registros[0].keys())
                t = doc.add_table(rows=1, cols=len(columnas))
                t.style = "Table Grid"

                for j, col_name in enumerate(columnas):
                    cell = t.rows[0].cells[j]
                    _colorear_celda(cell, "1B5E20")
                    p = cell.paragraphs[0]
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    run = p.add_run(str(col_name))
                    run.bold = True
                    run.font.size = Pt(7.5)
                    run.font.color.rgb = RGBColor(255, 255, 255)

                for idx_r, reg in enumerate(registros):
                    row_cells = t.add_row().cells
                    bg = "F1F8E9" if idx_r % 2 == 1 else "FFFFFF"
                    for j, col_name in enumerate(columnas):
                        val = reg[col_name]
                        _colorear_celda(row_cells[j], bg)
                        p = row_cells[j].paragraphs[0]
                        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        if pd.isna(val):
                            txt = "-"
                        elif isinstance(val, (int, float)) and float(val).is_integer():
                            txt = str(int(val))
                        elif isinstance(val, float):
                            txt = str(round(val, 1))
                        else:
                            txt = str(val)
                        run = p.add_run(txt)
                        run.font.size = Pt(8)

            doc.add_paragraph("")
            ruta_img = datos.get("ruta_grafica")
            if ruta_img and Path(ruta_img).exists():
                doc.add_picture(ruta_img, width=Inches(6.3))
            texto_ciclo = textos_ia.get("analisis_por_seccion", {}).get(nom_sec, {}).get(nom_ciclo, "")
            if texto_ciclo:
                doc.add_paragraph(texto_ciclo)

    doc.add_page_break()
    doc.add_heading("8. Síntesis Transversal y Recomendaciones Curriculares", level=1)
    doc.add_paragraph(textos_ia.get("sintesis_y_recomendaciones", ""))

    carpeta_destino.mkdir(parents=True, exist_ok=True)
    ruta_docx = carpeta_destino / f"{nombre_base}.docx"
    doc.save(str(ruta_docx))

    ruta_pdf, aviso_pdf = _convertir_a_pdf_local(ruta_docx, carpeta_destino)
    return {
        "ruta_docx": str(ruta_docx),
        "ruta_pdf": ruta_pdf,
        "aviso_pdf": aviso_pdf,
    }
