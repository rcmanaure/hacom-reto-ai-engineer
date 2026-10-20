"""Reglas deterministas: campos obligatorios, urgencia, prioridad/SLA, ruteo y escalamiento.

En producción las tablas viven en AppConfig (versionadas y validadas); aquí van inline.
Los valores son supuestos del diseño, no reglas reales del operador.
"""

CAMPOS_ALERTA = ("id", "origen", "equipo_id", "severidad", "timestamp")
CAMPOS_TICKET = ("id", "origen", "descripcion", "timestamp")

URGENCIA_SEVERIDAD = {"critical": "alta", "major": "media", "minor": "baja", "warning": "baja"}

# El Síntoma lo extrae el LLM del texto libre, pero la urgencia la fija esta tabla, no el modelo.
URGENCIA_SINTOMA = {"sin_servicio": "alta", "degradacion": "media", "intermitencia": "media", "consulta": "baja"}

MATRIZ_PRIORIDAD = {
    ("alto", "alta"): "P1", ("alto", "media"): "P2", ("alto", "baja"): "P3",
    ("medio", "alta"): "P2", ("medio", "media"): "P3", ("medio", "baja"): "P4",
    ("bajo", "alta"): "P3", ("bajo", "media"): "P4", ("bajo", "baja"): "P4",
}

SLA_RESPUESTA_MIN = {"P1": 15, "P2": 30, "P3": 120, "P4": 480}

RUTEO = {
    "router_core": "Core IP",
    "switch_agregacion": "Transporte",
    "olt": "Acceso FTTH",
    "bts": "Acceso Móvil",
    "firewall": "Seguridad",
}

ERRORES_NO_VERIFICABLE = {"ESQUEMA", "CITA_NO_DECLARADA", "CITA_INEXISTENTE", "HIPOTESIS_SIN_EVIDENCIA"}

# E7 marca degradación (sin análisis IA) pero no exige operador por sí sola.
CODIGOS_QUE_REQUIEREN_OPERADOR = {"E1", "E2", "E3", "E4", "E5", "E6"}

# Solo estos impiden derivar: sin datos o sin equipo claro. El resto se revisa en paralelo a la derivación.
CODIGOS_QUE_BLOQUEAN_DERIVACION = {"E1", "E3"}


def datos_evento(evento: dict) -> dict:
    """Campos del evento más los extraídos por el LLM (actividad 2, solo Tickets)."""
    return {**evento, **(evento.get("extraccion") or {})}


def campos_faltantes(evento: dict) -> list[str]:
    datos = datos_evento(evento)
    requeridos = CAMPOS_ALERTA if datos.get("tipo") == "alerta" else CAMPOS_TICKET
    faltan = [c for c in requeridos if not datos.get(c)]
    if datos.get("tipo") == "ticket":
        if not (datos.get("equipo_id") or datos.get("servicio_id")):
            faltan.append("equipo_id|servicio_id")
        if datos.get("sintoma") not in URGENCIA_SINTOMA:
            faltan.append("sintoma")
    return faltan


def urgencia(evento: dict) -> str:
    datos = datos_evento(evento)
    if datos["tipo"] == "alerta":
        return URGENCIA_SEVERIDAD[datos["severidad"]]
    return URGENCIA_SINTOMA[datos["sintoma"]]


def impacto(clientes_afectados: int, tier: str) -> str:
    if clientes_afectados >= 100 or tier == "oro":
        return "alto"
    if clientes_afectados >= 10 or tier == "plata":
        return "medio"
    return "bajo"


def prioridad(urg: str, clientes_afectados: int, tier: str) -> str:
    return MATRIZ_PRIORIDAD[(impacto(clientes_afectados, tier), urg)]


def ruteo(tipos_equipo: list[str]) -> str | None:
    """Equipo resolutor si la regla es unívoca; None si es ambiguo o desconocido."""
    equipos = {RUTEO.get(t) for t in tipos_equipo}
    if len(equipos) != 1 or None in equipos:
        return None
    return equipos.pop()


def codigos_escalamiento(prio: str, equipo: str | None, errores_resumen: list[str],
                         resumen, ia_disponible: bool) -> list[str]:
    codigos = set()
    if equipo is None:
        codigos.add("E3")
    if prio == "P1":
        codigos.add("E4")
    if not ia_disponible:
        codigos.add("E7")
        return sorted(codigos)
    if set(errores_resumen) & ERRORES_NO_VERIFICABLE:
        codigos.add("E2")
    if resumen is not None:
        if not resumen.investigacion_completa:
            codigos.add("E5")
        if any(a.tipo == "cambio" for a in resumen.acciones_sugeridas):
            codigos.add("E6")
    if "ACCION_SIN_AUTORIZACION" in errores_resumen or "ACCION_MAL_CLASIFICADA" in errores_resumen:
        codigos.add("E6")
    return sorted(codigos)


def requiere_operador(codigos: list[str]) -> bool:
    return bool(CODIGOS_QUE_REQUIEREN_OPERADOR & set(codigos))


def deriva_automaticamente(codigos: list[str]) -> bool:
    return not (CODIGOS_QUE_BLOQUEAN_DERIVACION & set(codigos))


def publica_resumen(ia_disponible: bool, errores_resumen: list[str]) -> bool:
    """Cualquier error del validador retiene el resumen hasta que lo revise el Operador NOC."""
    return ia_disponible and not errores_resumen
