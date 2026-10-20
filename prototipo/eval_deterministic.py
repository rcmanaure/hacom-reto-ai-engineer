"""Capa determinista de evaluación: corre casos.json contra reglas y validador de salida.

Uso: uv run --python 3.13 --with pydantic python eval_deterministic.py
Sale con código 1 si algún caso falla (apto como gate de CI).
Las salidas del modelo en casos.json son fijas (escritas a mano), no llamadas reales a un LLM.
"""
import json
import sys
from pathlib import Path

import reglas
from resumen import validar_resumen


def evaluar(caso: dict) -> dict:
    e = caso["entrada"]
    faltan = reglas.campos_faltantes(e["evento"])
    if faltan:
        return {"prioridad": None, "sla_min": None, "equipo": None,
                "escalamiento": ["E1"], "errores_resumen": [], "requiere_operador": True}

    ctx = e["contexto"]
    prio = reglas.prioridad(ctx["severidad"], ctx["clientes_afectados"], ctx["tier"])
    equipo = reglas.ruteo(ctx["tipos_equipo"])
    ia_disponible = e["salida_modelo"] is not None
    resumen, errores = (validar_resumen(e["salida_modelo"], set(e["trace_ids"]))
                        if ia_disponible else (None, []))
    codigos = reglas.codigos_escalamiento(prio, equipo, errores, resumen, ia_disponible)
    return {"prioridad": prio, "sla_min": reglas.SLA_RESPUESTA_MIN[prio], "equipo": equipo,
            "escalamiento": codigos, "errores_resumen": errores,
            "requiere_operador": reglas.requiere_operador(codigos)}


def main() -> int:
    casos = json.loads(Path(__file__).with_name("casos.json").read_text(encoding="utf-8"))
    fallos = 0
    for caso in casos:
        obtenido = evaluar(caso)
        diffs = {k: (v, obtenido[k]) for k, v in caso["esperado"].items() if obtenido[k] != v}
        estado = "OK  " if not diffs else "FAIL"
        fallos += bool(diffs)
        print(f"{estado} {caso['id']}  {caso['descripcion']}")
        for k, (esp, obt) in diffs.items():
            print(f"       {k}: esperado={esp} obtenido={obt}")
    print(f"\n{len(casos) - fallos}/{len(casos)} casos OK")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
