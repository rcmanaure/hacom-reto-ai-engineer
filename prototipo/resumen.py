"""Esquema de salida del resumen técnico (actividad 7) y su validación determinista."""
import re
from typing import Literal

from pydantic import BaseModel, Field, ValidationError


class Evidencia(BaseModel):
    evidence_id: str
    descripcion: str


class Hecho(BaseModel):
    texto: str
    evidencias: list[str] = Field(min_length=1)  # un hecho sin evidencia no es un hecho


class Hipotesis(BaseModel):
    texto: str
    probabilidad: Literal["alta", "media", "baja"]
    evidencias: list[str]


class AccionSugerida(BaseModel):
    texto: str
    tipo: Literal["diagnostico", "cambio"]
    requiere_autorizacion: bool


class ResumenTecnico(BaseModel):
    incidencia_id: str
    hechos: list[Hecho]
    hipotesis: list[Hipotesis]
    evidencias: list[Evidencia]
    acciones_sugeridas: list[AccionSugerida]
    equipo_sugerido: str | None = None
    investigacion_completa: bool


# shortcut: lista de verbos fija, solo detecta cambios obvios; reemplazar por un clasificador evaluado si hay falsos negativos en el golden set.
VERBOS_DE_CAMBIO = re.compile(
    r"\b(reinici\w*|reboot|reload|shutdown|apag\w*|configur\w*|cambi\w*|modific\w*|rollback|aplic\w*|bloque\w*|deshabilit\w*)\b",
    re.IGNORECASE,
)


def validar_resumen(salida: dict, trace_ids: set[str]) -> tuple[ResumenTecnico | None, list[str]]:
    """Devuelve (resumen, errores). trace_ids son los evidence_id que las tools devolvieron en esta ejecución."""
    try:
        r = ResumenTecnico.model_validate(salida)
    except ValidationError:
        return None, ["ESQUEMA"]

    errores: list[str] = []
    declaradas = {e.evidence_id for e in r.evidencias}
    citadas = {c for h in r.hechos for c in h.evidencias} | {c for h in r.hipotesis for c in h.evidencias}

    if citadas - declaradas:
        errores.append("CITA_NO_DECLARADA")
    if declaradas - trace_ids:
        errores.append("CITA_INEXISTENTE")  # evidencia que ninguna tool devolvió: alucinada
    if any(not h.evidencias for h in r.hipotesis):
        errores.append("HIPOTESIS_SIN_EVIDENCIA")
    for a in r.acciones_sugeridas:
        if a.tipo == "cambio" and not a.requiere_autorizacion:
            errores.append("ACCION_SIN_AUTORIZACION")
        if a.tipo == "diagnostico" and VERBOS_DE_CAMBIO.search(a.texto):
            errores.append("ACCION_MAL_CLASIFICADA")
    return r, sorted(set(errores))
