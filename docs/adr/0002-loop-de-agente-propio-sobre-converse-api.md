# Loop de agente propio sobre la Bedrock Converse API

El agente de investigación es un loop propio en Python, que usa la Bedrock Converse API con tool use y corre en una AWS Lambda invocada por el workflow una vez por Incidencia. Tiene límites duros: máximo 8 llamadas a tools, 90 s de timeout interno y un presupuesto de tokens. Si excede un límite, devuelve lo obtenido marcado como "investigación incompleta" (E5). Elegimos un loop propio para que cada límite, cada paso y cada traza sean visibles y explicables, en lugar de depender del comportamiento interno de un runtime gestionado.

## Opciones consideradas

- **Bedrock Agents (gestionado)**: descartado. El loop de orquestación y sus reintentos son opacos, y es más difícil imponer y demostrar los límites de pasos y tiempo.
- **Bedrock AgentCore (Runtime + Gateway)**: es una alternativa válida si la operación crece. Hoy añade componentes sin resolver un problema que el loop propio no resuelva.
- **ECS Fargate en lugar de Lambda**: descartado. Una tarea por Incidencia añade 30–60 s de arranque, y una ejecución de 90 s está muy por debajo del límite de 15 min de Lambda, que además es la plataforma del resto de los pasos.
