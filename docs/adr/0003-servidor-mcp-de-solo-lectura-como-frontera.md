# Servidor MCP de solo lectura como frontera de seguridad del agente

Las tools del agente se exponen desde un servidor MCP separado, detrás de un API Gateway privado y con un rol IAM que solo tiene permisos de lectura sobre los backends (monitoreo, catálogo, base relacional y RAG). El agente no tiene ninguna tool de escritura: las escrituras al Ticket maestro y la derivación las hace exclusivamente el workflow, con salidas ya validadas. Así, la garantía de que "la IA no ejecuta cambios sobre la red" la impone la infraestructura (IAM y la red), no el prompt, y se mantiene aunque el agente sufra prompt injection desde el texto de un Ticket o de un documento.

## Opciones consideradas

- **Tools como funciones locales dentro del contenedor del agente**: descartado. El proceso del agente tendría las credenciales de los backends, y el límite de acceso dependería del código de la tool en lugar de un rol separado y auditable.

## Consecuencias

- Las acciones sugeridas por el agente son solo texto. Ejecutarlas requiere el proceso de gestión de cambios del operador, fuera de esta solución.
