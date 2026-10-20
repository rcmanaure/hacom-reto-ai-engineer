# Workflow determinista con un único agente de investigación

Las 8 actividades las orquesta un workflow determinista en AWS Step Functions (Standard), con un estado por actividad y `waitForTaskToken` para la aprobación del Operador NOC. El único agente IA se invoca en la actividad 5 (investigar causas probables), porque es la única donde la ruta de consulta no es predecible. La extracción de campos (actividad 4) y el resumen técnico (actividad 7) son llamadas LLM puntuales dentro del workflow, no agentes. Así, el control de flujo, el SLA, el ruteo y el escalamiento quedan en código auditable.

## Opciones consideradas

- **Un agente orquestador que hace todo**: descartado. Delega al LLM decisiones que tienen reglas conocidas (SLA, prioridad, ruteo) y vuelve no auditable el flujo.
- **Multi-agente, uno por actividad**: descartado. Multiplica costo, latencia y superficie de fallo sin ganar capacidad, y el reto penaliza explícitamente la complejidad innecesaria.
- **Temporal o LangGraph sobre ECS como orquestador**: descartado. Añade un servicio que hay que operar, mientras que Step Functions da historial de ejecución, reintentos y pausa humana gestionados.
