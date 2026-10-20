# Reto técnico AI Engineer · Gestión de Incidencias de Red

Propuesta de diseño para que un equipo de operaciones de red atienda incidencias más rápido y con mejor trazabilidad, usando inteligencia artificial solo donde aporta y sin que la IA pueda hacer cambios sobre la red.

> **Importante:** esto es un **diseño**, no un sistema en producción. Incluye un prototipo pequeño que sí se puede ejecutar (reglas y pruebas), pero no se desplegó infraestructura ni se usó un modelo de IA real.

---

## Si vas a evaluar la entrega (no necesitas instalar nada)

Todo se puede ver desde el navegador, haciendo clic en los enlaces. Orden sugerido:

| Paso | Qué abrir | Qué vas a encontrar | Tiempo |
|---|---|---|---|
| 1 | [**Documento técnico (PDF)**](docs/entregable/HACOM-Reto-AI-Engineer.pdf) | La propuesta completa: 20 páginas con índice. Empieza por el resumen ejecutivo (pág. 2). | 15–25 min |
| 2 | **Video de presentación** | Resumen de menos de 4 minutos que recorre las decisiones y los diagramas. Se entrega por el canal indicado por HACOM. | 4 min |
| 3 | [Diagrama lógico](docs/entregable/diagramas/logica.png) · [Diagrama de estados](docs/entregable/diagramas/estados.png) · [Diagrama físico](docs/entregable/diagramas/fisica.png) | Los mismos diagramas del documento, en alta resolución para hacer zoom. | 5 min |
| 4 | [Resultado de las pruebas del prototipo](prototipo/resultado-evaluacion.txt) | Los 20 casos de prueba y su resultado (20/20 OK), sin necesidad de ejecutar nada. | 2 min |

Si una palabra no es clara (por ejemplo *Incidencia*, *Síntoma* u *Operador NOC*), está definida en el [glosario](GLOSSARY.md).

### Dónde está cada punto del enunciado

| Lo que pide el reto | Dónde está |
|---|---|
| Matriz de decisiones de automatización | Documento §3 (págs. 3–5) |
| Arquitectura conceptual / lógica | Documento §4 (pág. 6) · [diagrama lógico](docs/entregable/diagramas/logica.png) · [diagrama de estados](docs/entregable/diagramas/estados.png) |
| Arquitectura física y su justificación | Documento §5 (pág. 11) · [diagrama físico](docs/entregable/diagramas/fisica.png) |
| Riesgos y controles de seguridad | Documento §6 (pág. 14) |
| Estrategia de evaluación de la IA generativa | Documento §7 (pág. 15) · [prototipo](prototipo/) |
| Supuestos, limitaciones y decisiones técnicas | Documento §2 (pág. 3), §8 (pág. 17), §9 (pág. 18) · [decisiones de arquitectura](docs/adr/) |
| Video de presentación | Se entrega aparte |
| Prototipo (opcional) | [`prototipo/`](prototipo/) · Documento, Anexo A (pág. 19) |

### Cómo responde al criterio central de evaluación

| Criterio | Cómo se cubre | Dónde verlo |
|---|---|---|
| **Calidad del razonamiento técnico** | Todas las decisiones parten de un principio explícito: reglas donde hay reglas e IA solo donde aporta. Los supuestos (S1–S8) y los riesgos residuales están declarados, y se separa lo implementado de lo que es solo diseño. | Documento §1, §2 y §8.5 |
| **Selección del tipo de automatización por actividad** | Una matriz de las 8 actividades con el tipo elegido, por qué y la alternativa descartada (LLM, agente o ML clásico), y una tabla que clasifica cada actividad. Resultado: arquitectura híbrida con 2 workflows IA y 1 agente IA. | Documento §3 (págs. 3–5) |
| **Diseño seguro y evaluable** | La IA no tiene permisos de escritura (lo impone IAM, no el prompt), los datos personales se seudonimizan y un validador retiene cualquier resumen con errores. Cada control dice cómo se verifica. La evaluación tiene 3 capas con métricas y umbrales, y el prototipo trae 20 casos ejecutables. | Documento §6 (pág. 14) y §7 (pág. 15) · [prototipo](prototipo/) |
| **Capacidad de justificar las decisiones** | Cada tabla incluye las alternativas descartadas y por qué. Las decisiones difíciles de revertir tienen un ADR, y el documento responde de antemano las preguntas que haría un evaluador. | Documento §5, §9 y §10 (pág. 19) · [ADRs](docs/adr/) |

### La propuesta en 30 segundos

- **Casi todo el proceso son reglas fijas**, no IA: validar, priorizar, calcular el plazo de atención (SLA), decidir a qué equipo va la incidencia y escribir en el ticket. Así es exacto y auditable.
- **La IA se usa en tres puntos**: leer tickets escritos en texto libre, investigar causas probables (un único "agente") y redactar un resumen técnico.
- **La incidencia llega al equipo correcto en segundos**, sin esperar a la IA. El análisis se agrega después como nota.
- **La IA no puede tocar la red**: solo tiene permisos de lectura, y todo lo que escribe pasa por una verificación automática. Si algo no cuadra, una persona del NOC lo revisa antes de publicarlo.

---

## Si eres técnico

### Mapa del repositorio

```
.
├── README.md                     esta guía
├── GLOSSARY.md                   lenguaje del dominio (Alerta, Ticket, Incidencia, Síntoma…)
├── docs/
│   ├── adr/                      decisiones de arquitectura (ADR 0001–0003)
│   └── entregable/
│       ├── documento-tecnico.md  fuente del documento (el PDF y el DOCX salen de aquí)
│       ├── HACOM-Reto-AI-Engineer.pdf / .docx
│       ├── exportar.ps1          genera el DOCX y el PDF
│       └── diagramas/            logica.dot · estados.mmd · fisica.py → PNG
└── prototipo/
    ├── tools.json                contratos (JSON Schema) de las 6 tools MCP de solo lectura
    ├── resumen.py                esquema de salida del resumen y validador determinista
    ├── reglas.py                 urgencia, prioridad/SLA, ruteo, escalamiento, derivación, publicación
    ├── casos.json                20 casos de evaluación
    ├── eval_deterministic.py     corre los casos; código de salida 1 si alguno falla
    └── resultado-evaluacion.txt  última salida de la evaluación
```

### Tesis técnica

Un workflow determinista (Step Functions) orquesta las 8 actividades. Un único agente (loop propio sobre la Bedrock Converse API, en Lambda, ≤8 llamadas a tools y ≤90 s) investiga causas con tools MCP de solo lectura. Dos llamadas LLM puntuales extraen campos de Tickets y redactan el resumen. Urgencia, prioridad, SLA, ruteo, escalamiento y escritura quedan fuera del LLM.

Orden de ejecución: recibir → extraer y validar → enriquecer → priorizar → **derivar por regla** → investigar → resumir → validar → nota interna en el ticket. Solo E1 (faltan datos) y E3 (ruteo ambiguo) bloquean la derivación. Cualquier error del validador retiene el resumen.

Decisiones clave:

1. [Workflow determinista con un único agente](docs/adr/0001-workflow-determinista-con-un-solo-agente.md), no un agente orquestador ni multi-agente.
2. [Loop de agente propio sobre la Bedrock Converse API](docs/adr/0002-loop-de-agente-propio-sobre-converse-api.md), en Lambda y con límites duros.
3. [Servidor MCP de solo lectura como frontera de seguridad](docs/adr/0003-servidor-mcp-de-solo-lectura-como-frontera.md): la garantía de no actuar sobre la red la da IAM, no el prompt.

### Requisitos

| Para | Necesitas |
|---|---|
| Ejecutar la evaluación | [uv](https://docs.astral.sh/uv/) (descarga Python 3.13 y las dependencias solo) |
| Regenerar diagramas | [Graphviz](https://graphviz.org/) en el PATH y [mermaid-cli](https://github.com/mermaid-js/mermaid-cli) (`mmdc`) |
| Regenerar el DOCX y el PDF | Windows con PowerShell, uv y Microsoft Word |

### Ejecutar la evaluación determinista

```bash
cd prototipo
uv run --python 3.13 --with pydantic python eval_deterministic.py
```

Corre 20 casos: normales, Tickets en texto libre, escalamiento, entradas fuera de catálogo, acción de cambio inducida, cita alucinada, acción disfrazada, falso positivo e IA caída. En cada uno comprueba prioridad, SLA, equipo, códigos de escalamiento, si se deriva y si el resumen se publica o se retiene. Las salidas del modelo en `casos.json` son fijas: se prueba el validador y las reglas, no la calidad de un modelo.

Si cambias reglas o casos, actualiza el resultado versionado:

```bash
PYTHONIOENCODING=utf-8 uv run --python 3.13 --with pydantic python eval_deterministic.py > resultado-evaluacion.txt
```

### Regenerar diagramas y documento

```bash
cd docs/entregable/diagramas
dot -Tpng -Gdpi=150 logica.dot -o logica.png
mmdc -q -i estados.mmd -o estados.png -s 2
uv run --python 3.13 --with diagrams python fisica.py
```

```powershell
docs\entregable\exportar.ps1
```

`exportar.ps1` convierte el Markdown con pandoc, da formato a las tablas, pone el diagrama lógico en una página horizontal y el de estados en una página propia, y exporta a PDF. Edita siempre `documento-tecnico.md`, nunca el DOCX: el script lo sobrescribe.

### Qué está implementado y qué no

| Implementado y probado | Solo diseño |
|---|---|
| Reglas deterministas, validador de salida, contratos de tools y 20 casos de evaluación | Loop del agente, servidor MCP, enmascarado de PII, definición de Step Functions, infraestructura AWS y cualquier llamada a un modelo real |
