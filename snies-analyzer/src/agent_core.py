"""Agente conversacional local — Human-in-the-loop 50/50 (sin API keys).

50% agente: inspección, propuestas, cálculos, gráficas e informe.
50% humano: confirma cada etapa del chat antes de avanzar.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable


SALUDO_RE = re.compile(
    r"\b(hola|buenos\s+d[ií]as|buenas\s+tardes|buenas\s+noches|saludos|hey)\b",
    re.I,
)
CONFIRMAR_RE = re.compile(
    r"\b(s[ií]|ok|vale|confirmo|correcto|de\s+acuerdo|procede|adelante|acepto|contin[uú]a|listo|genera|generar)\b",
    re.I,
)
NEGAR_RE = re.compile(r"\b(no|cancelar|detener|espera|incorrecto|cambiar|faltan|atras|atrás)\b", re.I)
SOLO_UN_CICLO_RE = re.compile(
    r"\b(solo\s+un\s+ciclo|solo\s+tecnico|solo\s+t[eé]cnico|es\s+el\s+unico|es\s+el\s+[uú]nico|unicamente|únicamente)\b",
    re.I,
)

# Etapas visibles del flujo 50/50
ETAPAS = [
    ("esperando_insumos", "1/6 Insumos CSV"),
    ("confirmar_contexto", "2/6 Programa y sede"),
    ("validacion_snies", "3/6 Mapeo SNIES"),
    ("confirmar_cobertura", "4/6 Cobertura de ciclos"),
    ("confirmar_alcance", "5/6 Alcance del informe"),
    ("confirmar_generacion", "6/6 Autorizar generación"),
]


def _etiqueta_etapa(estado: str) -> str:
    for key, label in ETAPAS:
        if key == estado:
            return label
    if estado == "alerta":
        return "Pausa por novedad"
    if estado == "listo":
        return "Completado — revisión conjunta"
    return estado


def _extraer_programa_sede(texto: str) -> tuple[str | None, str | None]:
    m_prog = re.search(r"programa\s*[:=-]?\s*[«\"']?([^,\"'\n]+)[»\"']?", texto, re.I)
    m_sede = re.search(r"sede\s*[:=-]?\s*[«\"']?([^,\"'\n]+)[»\"']?", texto, re.I)
    return (
        m_prog.group(1).strip() if m_prog else None,
        m_sede.group(1).strip() if m_sede else None,
    )


def _proponer_mapeo(snies_detectados: list[dict]) -> dict[str, int]:
    items = [d for d in snies_detectados if d.get("puntaje_global_promedio") is not None]
    items.sort(key=lambda d: float(d["puntaje_global_promedio"]))
    propuesta: dict[str, int] = {"tecnico": 0, "tecnologo": 0, "profesional": 0}
    if not items:
        return propuesta
    if len(items) == 1:
        d = items[0]
        clave = "profesional" if float(d["puntaje_global_promedio"]) >= 125 else "tecnico"
        propuesta[clave] = int(d["snies"])
        return propuesta
    if len(items) == 2:
        a, b = items[0], items[1]
        if float(b["puntaje_global_promedio"]) >= 125 and float(a["puntaje_global_promedio"]) < 125:
            propuesta["tecnico"] = int(a["snies"])
            propuesta["profesional"] = int(b["snies"])
        else:
            propuesta["tecnico"] = int(a["snies"])
            propuesta["tecnologo"] = int(b["snies"])
        return propuesta
    propuesta["tecnico"] = int(items[0]["snies"])
    propuesta["tecnologo"] = int(items[1]["snies"])
    propuesta["profesional"] = int(items[-1]["snies"])
    return propuesta


def _parsear_mapeo_manual(texto: str) -> dict[str, int]:
    out = {"tecnico": 0, "tecnologo": 0, "profesional": 0}
    patrones = {
        "tecnico": r"t[eé]cnic[oa]\s*[:=-]?\s*(\d{4,})",
        "tecnologo": r"tecn[oó]log[oa]\s*[:=-]?\s*(\d{4,})",
        "profesional": r"profesional\s*[:=-]?\s*(\d{4,})",
    }
    for k, pat in patrones.items():
        m = re.search(pat, texto, re.I)
        if m:
            out[k] = int(m.group(1))
    for m in re.finditer(r"(?:snies\s*)?(\d{5,})\s*(t[eé]cnic|tecn[oó]log|profesional)", texto, re.I):
        num = int(m.group(1))
        etiqueta = m.group(2).lower()
        if etiqueta.startswith("tecnic") or etiqueta.startswith("técnic"):
            out["tecnico"] = num
        elif "tecnolog" in etiqueta:
            out["tecnologo"] = num
        else:
            out["profesional"] = num
    return out


@dataclass
class RespuestaAgente:
    text: str
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class SesionAgenteLocal:
    inspeccionar_fn: Callable[[], dict]
    ejecutar_fn: Callable[..., dict]
    estado: str = "inicio"
    programa: str = ""
    sede: str = ""
    mapeo_propuesto: dict[str, int] = field(
        default_factory=lambda: {"tecnico": 0, "tecnologo": 0, "profesional": 0}
    )
    mapeo_confirmado: dict[str, int] = field(
        default_factory=lambda: {"tecnico": 0, "tecnologo": 0, "profesional": 0}
    )
    ultimo_inspeccion: dict | None = None
    ultimo_resultado: dict | None = None
    forzar_continuar_con_alertas: bool = False
    cobertura_ok: bool = False
    alcance_ok: bool = False

    def _prefijo(self) -> str:
        return f"🧭 **HITL 50/50 · {_etiqueta_etapa(self.estado)}**\n\n"

    def send_message(self, prompt: str) -> RespuestaAgente:
        texto = (prompt or "").strip()
        bajo = texto.lower()

        prog, sede = _extraer_programa_sede(texto)
        if prog:
            self.programa = prog
        if sede:
            self.sede = sede

        mapeo_msg = _parsear_mapeo_manual(texto)
        if any(mapeo_msg.values()):
            for k, v in mapeo_msg.items():
                if v:
                    self.mapeo_confirmado[k] = v
                    self.mapeo_propuesto[k] = v

        # --- Saludo / reinicio conversacional ---
        if self.estado == "inicio" or (
            SALUDO_RE.search(bajo) and self.estado in ("inicio", "esperando_insumos", "listo")
        ):
            self._reset_parcial()
            self.estado = "esperando_insumos"
            return RespuestaAgente(text=self._prefijo() + self._texto_saludo())

        # --- Alerta ---
        if self.estado == "alerta":
            if NEGAR_RE.search(bajo):
                self.estado = "esperando_insumos"
                return RespuestaAgente(
                    text=self._prefijo()
                    + "Me detengo contigo en este punto. Corrige los CSV y escribe **inspeccionar**."
                )
            if CONFIRMAR_RE.search(bajo):
                self.forzar_continuar_con_alertas = True
                if self.ultimo_inspeccion and self.ultimo_inspeccion.get("snies_detectados"):
                    return self._presentar_propuesta_snies(self.ultimo_inspeccion)
                return self._inspeccionar()
            return RespuestaAgente(
                text=self._prefijo()
                + "Hay una novedad abierta. Responde **sí** para continuar o **no** para corregir insumos."
            )

        # Etapa 1: CSV listos → pedir / confirmar contexto
        if self.estado == "esperando_insumos":
            quiere_avanzar = any(
                k in bajo for k in ("inspeccion", "revisa", "listo", "csv", "cargados", "subidos")
            ) or CONFIRMAR_RE.search(bajo)
            if self.programa and self.sede and quiere_avanzar:
                self.estado = "confirmar_contexto"
                return self._inspeccionar()
            if quiere_avanzar and not (self.programa and self.sede):
                self.estado = "confirmar_contexto"
                return RespuestaAgente(
                    text=self._prefijo()
                    + "Antes de inspeccionar, necesito tu mitad del flujo:\n"
                    "Indica `programa: NOMBRE` y `sede: SEDE`, luego responde **sí**."
                )
            if self.programa and self.sede:
                self.estado = "confirmar_contexto"
                return RespuestaAgente(
                    text=self._prefijo()
                    + f"Quedó: programa **{self.programa}**, sede **{self.sede}**.\n"
                    "¿Confirmas este contexto para inspeccionar los CSV? Responde **sí** o corrige."
                )
            return RespuestaAgente(
                text=self._prefijo()
                + "Carga los 2 CSV en el panel y dime `programa: …, sede: …` "
                "o escribe **listo** cuando estén cargados."
            )

        # Etapa 2: confirmar programa/sede y luego inspeccionar
        if self.estado == "confirmar_contexto":
            if NEGAR_RE.search(bajo):
                self.programa = ""
                self.sede = ""
                self.estado = "esperando_insumos"
                return RespuestaAgente(
                    text=self._prefijo()
                    + "Sin problema. Indica de nuevo `programa: …` y `sede: …`."
                )
            if self.programa and self.sede and CONFIRMAR_RE.search(bajo):
                return self._inspeccionar()
            if self.programa and self.sede:
                return RespuestaAgente(
                    text=self._prefijo()
                    + f"Contexto actual: **{self.programa}** / **{self.sede}**.\n"
                    "¿Lo confirmamos para inspeccionar? Responde **sí**."
                )
            return RespuestaAgente(
                text=self._prefijo()
                + "Aún faltan programa y/o sede. Ejemplo: "
                "`programa: Administracion de Servicios de salud, sede: Bogota`"
            )

        # Etapa 3: mapeo SNIES
        if self.estado == "validacion_snies":
            if NEGAR_RE.search(bajo) and not any(mapeo_msg.values()):
                return RespuestaAgente(
                    text=self._prefijo()
                    + "Corrige el mapeo así:\n"
                    "`tecnico 14162, tecnologo 0, profesional 0`\n"
                    "Luego responde **sí**."
                )
            if any(mapeo_msg.values()) or CONFIRMAR_RE.search(bajo):
                if not any(self.mapeo_confirmado.values()):
                    self.mapeo_confirmado = dict(self.mapeo_propuesto)
                return self._pedir_cobertura()
            return RespuestaAgente(
                text=self._prefijo()
                + "Tu turno: confirma el mapeo SNIES con **sí** o corrígelo manualmente."
            )

        # Etapa 4: cobertura de ciclos (siempre en 50/50)
        if self.estado == "confirmar_cobertura":
            if NEGAR_RE.search(bajo) or "faltan" in bajo:
                self.estado = "esperando_insumos"
                return RespuestaAgente(
                    text=self._prefijo()
                    + "No genero aún. Carga los SNIES/ciclos faltantes y escribe **inspeccionar**."
                )
            if CONFIRMAR_RE.search(bajo) or SOLO_UN_CICLO_RE.search(bajo):
                self.cobertura_ok = True
                return self._pedir_alcance()
            return RespuestaAgente(
                text=self._prefijo()
                + "¿La cobertura de ciclos es correcta?\n"
                "- **sí** / **sí, solo un ciclo**\n"
                "- **no, faltan**"
            )

        # Etapa 5: alcance del informe
        if self.estado == "confirmar_alcance":
            if NEGAR_RE.search(bajo):
                self.estado = "validacion_snies"
                return RespuestaAgente(
                    text=self._prefijo()
                    + "Volvemos al mapeo SNIES. Confirma o corrige y responde **sí**."
                )
            if CONFIRMAR_RE.search(bajo) or "alcance" in bajo or "globales" in bajo:
                self.alcance_ok = True
                return self._plan_de_generacion()
            return RespuestaAgente(
                text=self._prefijo()
                + "¿Confirmas el alcance?\n"
                "**Resultados Globales** + 5 competencias genéricas + Word/PDF.\n"
                "Responde **sí** o **no**."
            )

        # Etapa 6: autorizar generación
        if self.estado == "confirmar_generacion":
            if NEGAR_RE.search(bajo):
                self.estado = "confirmar_alcance"
                return RespuestaAgente(
                    text=self._prefijo() + "Generación cancelada. ¿Ajustamos el alcance? Responde **sí** o **no**."
                )
            if CONFIRMAR_RE.search(bajo) or "generar" in bajo or "ejecut" in bajo:
                return self._intentar_ejecutar()
            return RespuestaAgente(
                text=self._prefijo()
                + "Para lanzar el informe responde **sí, generar**."
            )

        # Post-análisis
        if self.estado == "listo":
            if any(k in bajo for k in ("otro", "nuevo", "inspeccion", "hola")):
                self._reset_parcial()
                self.estado = "esperando_insumos"
                return RespuestaAgente(text=self._prefijo() + self._texto_saludo())
            return RespuestaAgente(
                text=self._prefijo()
                + "¿Quieres revisar el Word/PDF juntos, ajustar algo o analizar **otro programa**?"
            )

        # Comandos globales útiles
        if any(k in bajo for k in ("inspeccion", "revisa", "revisar")):
            return self._inspeccionar()

        return RespuestaAgente(
            text=self._prefijo()
            + "Estamos en flujo **50/50**. Dime en qué etapa estás o escribe:\n"
            "- `programa: …, sede: …`\n"
            "- **sí** / **no**\n"
            "- **inspeccionar**\n"
            "- **sí, generar**"
        )

    def _reset_parcial(self) -> None:
        self.forzar_continuar_con_alertas = False
        self.cobertura_ok = False
        self.alcance_ok = False
        self.ultimo_resultado = None

    def _texto_saludo(self) -> str:
        return (
            "Soy **Snies Analyzer**, Analista ICFES (Saber TyT / Saber Pro) para la CUN.\n\n"
            "Trabajamos en **Human-in-the-loop 50/50**:\n"
            "- **50% yo:** inspecciono, propongo SNIES, calculo, grafico y documento.\n"
            "- **50% tú:** confirmas cada etapa en el chat antes de avanzar.\n\n"
            "**Etapas:** insumos → programa/sede → mapeo SNIES → cobertura → alcance → generar.\n\n"
            "Empieza cargando los 2 CSV y escribe:\n"
            "`programa: …, sede: …`"
        )

    def _inspeccionar(self) -> RespuestaAgente:
        result = self.inspeccionar_fn()
        self.ultimo_inspeccion = result
        self.cobertura_ok = False
        self.alcance_ok = False

        if not result.get("ok"):
            self.estado = "alerta"
            alertas = result.get("alertas_10_porciento") or ["Error de inspección"]
            bullets = "\n".join(f"- {a}" for a in alertas)
            return RespuestaAgente(
                text=self._prefijo()
                + "Detecté bloqueos en la inspección:\n"
                f"{bullets}\n\n¿Intentamos continuar igual (**sí**) o corregimos (**no**)?",
                meta=result,
            )

        alertas = result.get("alertas_10_porciento") or []
        if alertas and not self.forzar_continuar_con_alertas:
            self.estado = "alerta"
            bullets = "\n".join(f"- {a}" for a in alertas)
            return RespuestaAgente(
                text=self._prefijo()
                + "Inspección con novedades:\n"
                f"{bullets}\n\n¿Continuamos con validación SNIES? **sí** / **no**",
                meta=result,
            )

        return self._presentar_propuesta_snies(result)

    def _presentar_propuesta_snies(self, result: dict) -> RespuestaAgente:
        snies = result.get("snies_detectados") or []
        self.mapeo_propuesto = _proponer_mapeo(snies)
        self.mapeo_confirmado = dict(self.mapeo_propuesto)
        self.estado = "validacion_snies"

        lineas = [
            f"- SNIES **{d['snies']}** | años {d['rango_anios']} | "
            f"promedio {d['puntaje_global_promedio']} | {d['orientacion']}"
            for d in snies
        ]
        prop = self.mapeo_propuesto
        propuesta_txt = (
            f"- TyT – Técnico → `{prop.get('tecnico') or '—'}`\n"
            f"- TyT – Tecnólogo → `{prop.get('tecnologo') or '—'}`\n"
            f"- Saber Pro – Profesional → `{prop.get('profesional') or '—'}`"
        )
        return RespuestaAgente(
            text=self._prefijo()
            + "Inspección lista. SNIES detectados:\n"
            + ("\n".join(lineas) if lineas else "- Ninguno")
            + "\n\n**Mi propuesta de mapeo (tu confirmación es obligatoria):**\n"
            + propuesta_txt
            + f"\n\nContexto: **{self.programa or '—'}** / **{self.sede or '—'}**\n\n"
            + "Responde **sí** para aceptar o corrige con `tecnico …, tecnologo …, profesional …`.",
            meta={**result, "mapeo_propuesto": self.mapeo_propuesto},
        )

    def _pedir_cobertura(self) -> RespuestaAgente:
        self.estado = "confirmar_cobertura"
        snies_n = len(self.ultimo_inspeccion.get("snies_detectados", [])) if self.ultimo_inspeccion else 0
        if snies_n <= 1:
            pregunta = (
                "Solo hay **1 SNIES**. ¿El programa tiene un solo ciclo "
                "o faltan Tecnólogo/Profesional?\n"
                "Responde **sí, solo un ciclo** o **no, faltan**."
            )
        else:
            pregunta = (
                f"Hay **{snies_n} SNIES**. ¿Confirmas que la cobertura de ciclos "
                "Técnico/Tecnólogo/Profesional quedó bien asignada?\n"
                "Responde **sí** o **no, faltan**."
            )
        return RespuestaAgente(text=self._prefijo() + pregunta)

    def _pedir_alcance(self) -> RespuestaAgente:
        self.estado = "confirmar_alcance"
        n = sum(1 for v in self.mapeo_confirmado.values() if v)
        return RespuestaAgente(
            text=self._prefijo()
            + "Confirmemos el **alcance del informe**:\n"
            f"- Resultados Globales por ciclo ({n} ciclo/s)\n"
            "- 5 competencias genéricas\n"
            f"- Hasta **{6 * n}** tablas/gráficas + Word + PDF\n\n"
            "¿Este alcance es correcto? Responde **sí** o **no**."
        )

    def _plan_de_generacion(self) -> RespuestaAgente:
        if not self.programa or not self.sede:
            self.estado = "confirmar_contexto"
            return RespuestaAgente(
                text=self._prefijo() + "Falta programa/sede. Complétalos y confirma con **sí**."
            )
        if not any(self.mapeo_confirmado.values()):
            self.estado = "validacion_snies"
            return RespuestaAgente(text=self._prefijo() + "Falta mapeo SNIES. Confirma o corrige.")

        self.estado = "confirmar_generacion"
        ciclos = []
        if self.mapeo_confirmado.get("tecnico"):
            ciclos.append(f"TyT – Técnico ({self.mapeo_confirmado['tecnico']})")
        if self.mapeo_confirmado.get("tecnologo"):
            ciclos.append(f"TyT – Tecnólogo ({self.mapeo_confirmado['tecnologo']})")
        if self.mapeo_confirmado.get("profesional"):
            ciclos.append(f"Saber Pro – Profesional ({self.mapeo_confirmado['profesional']})")

        return RespuestaAgente(
            text=self._prefijo()
            + "📋 **Resumen final antes de generar**\n\n"
            f"- Programa: **{self.programa}**\n"
            f"- Sede: **{self.sede}**\n"
            f"- Ciclos: {', '.join(ciclos)}\n"
            "- Incluye: Resultados Globales + 5 competencias + Word/PDF\n\n"
            "Tu autorización (50% humano): responde **sí, generar**.",
            meta={"mapeo": self.mapeo_confirmado, "ciclos": ciclos},
        )

    def _intentar_ejecutar(self) -> RespuestaAgente:
        if not self.programa or not self.sede or not any(self.mapeo_confirmado.values()):
            self.estado = "confirmar_contexto"
            return RespuestaAgente(
                text=self._prefijo() + "No puedo generar aún: faltan confirmaciones previas."
            )

        self.estado = "ejecutando"
        resultado = self.ejecutar_fn(
            nombre_programa=self.programa,
            sede=self.sede,
            snies_tecnico=int(self.mapeo_confirmado.get("tecnico") or 0),
            snies_tecnologo=int(self.mapeo_confirmado.get("tecnologo") or 0),
            snies_profesional=int(self.mapeo_confirmado.get("profesional") or 0),
        )
        self.ultimo_resultado = resultado

        if resultado.get("estado") != "completado":
            self.estado = "alerta"
            return RespuestaAgente(
                text=self._prefijo()
                + f"Falló la generación:\n{resultado.get('detalle', resultado)}\n\n"
                "**sí** para reintentar ruta / **no** para corregir.",
                meta=resultado,
            )

        self.estado = "listo"
        secs = resultado.get("secciones_generadas") or {}
        secs_txt = "\n".join(f"- {k}: {', '.join(v)}" for k, v in secs.items()) or "- (sin detalle)"
        msg = (
            self._prefijo()
            + "✅ Informe generado. Revisemos juntos el resultado:\n\n"
            f"- Carpeta: `{resultado['carpeta_local']}`\n"
            f"- Tablas/gráficas: **{resultado.get('total_tablas_y_graficas')}**\n"
            f"- Word: `{resultado.get('ruta_docx')}`\n"
            f"- PDF: `{resultado.get('ruta_pdf') or 'No generado'}`\n\n"
            f"Secciones:\n{secs_txt}\n"
        )
        if resultado.get("aviso_pdf"):
            msg += f"\n⚠️ {resultado['aviso_pdf']}"
        if resultado.get("alertas"):
            msg += "\n\nAlertas:\n" + "\n".join(f"- {a}" for a in resultado["alertas"])
        msg += "\n\n¿El entregable está OK, quieres ajustar algo o analizamos **otro programa**?"
        return RespuestaAgente(text=msg, meta=resultado)

    def actualizar_contexto(
        self,
        programa: str = "",
        sede: str = "",
        snies_tecnico: int = 0,
        snies_tecnologo: int = 0,
        snies_profesional: int = 0,
    ) -> None:
        if programa:
            self.programa = programa.strip()
        if sede:
            self.sede = sede.strip()
        if snies_tecnico:
            self.mapeo_confirmado["tecnico"] = int(snies_tecnico)
            self.mapeo_propuesto["tecnico"] = int(snies_tecnico)
        if snies_tecnologo:
            self.mapeo_confirmado["tecnologo"] = int(snies_tecnologo)
            self.mapeo_propuesto["tecnologo"] = int(snies_tecnologo)
        if snies_profesional:
            self.mapeo_confirmado["profesional"] = int(snies_profesional)
            self.mapeo_propuesto["profesional"] = int(snies_profesional)


def crear_sesion_chat(tools_list: list) -> SesionAgenteLocal:
    inspeccionar_fn = tools_list[0]
    ejecutar_fn = tools_list[1] if len(tools_list) > 1 else (lambda **_: {})
    return SesionAgenteLocal(inspeccionar_fn=inspeccionar_fn, ejecutar_fn=ejecutar_fn)
