"""Diagrama de arquitectura física (AWS + on-prem).

Render: uv run --python 3.13 --with diagrams python fisica.py  (requiere Graphviz en PATH)
"""
from diagrams import Cluster, Diagram, Edge
from diagrams.aws.compute import Lambda
from diagrams.aws.database import Aurora
from diagrams.aws.integration import EventbridgePipes, SQS, StepFunctions
from diagrams.aws.management import Cloudtrail, Cloudwatch, SystemsManagerAppConfig
from diagrams.aws.ml import Bedrock
from diagrams.aws.network import APIGateway, DirectConnect, Endpoint, SiteToSiteVpn
from diagrams.aws.security import KMS, SecretsManager, SingleSignOn
from diagrams.aws.storage import S3
from diagrams.generic.compute import Rack
from diagrams.generic.database import SQL
from diagrams.generic.storage import Storage
from diagrams.onprem.client import Users

graph_attr = {"fontsize": "14", "pad": "0.4", "nodesep": "0.6", "ranksep": "0.8", "splines": "spline"}

# Sin título en la imagen: el documento ya pone la leyenda de la figura.
with Diagram("", filename="fisica", outformat="png",
             direction="TB", graph_attr=graph_attr, show=False):

    # Iconos genéricos: el diseño no supone productos concretos on-prem.
    with Cluster("Operador · on-prem"):
        mon = Rack("Monitoreo (NMS)")
        tickets = Storage("Plataforma de tickets")
        catalogo = Storage("Catálogo clientes/servicios")
        bd = SQL("BD relacional\ninventario/topología")
        repos = Storage("Repos documentación")
        noc = Users("Operador NOC")

    with Cluster("Enlace privado"):
        dx = DirectConnect("Direct Connect\n+ Route 53 Resolver")
        vpn = SiteToSiteVpn("VPN respaldo")

    with Cluster("AWS · cuenta dedicada por operador"):
        with Cluster("VPC privada (sin salida a Internet)"):
            apigw = APIGateway("API Gateway privado\nwebhooks: eventos\ny aprobaciones")
            cola = SQS("SQS + DLQ")
            pipes = EventbridgePipes("EventBridge Pipes")
            sfn = StepFunctions("Step Functions\nStandard")
            with Cluster("Pasos deterministas"):
                lam = Lambda("Pasos del\nworkflow")
                writer = Lambda("ticket-writer\n(único con\nescritura)")
            agente = Lambda("Agente\n≤8 llamadas, ≤90 s\nconcurrencia limitada")
            apigw_mcp = APIGateway("API Gateway privado\nMCP (IAM auth)")
            mcp = Lambda("Servidor MCP\nsolo lectura")
            aurora = Aurora("Aurora PostgreSQL\nServerless v2 + RDS Proxy\nestado + auditoría + pgvector")
            vpce = Endpoint("VPC endpoints\n(lista en §5)")

        with Cluster("Servicios gestionados"):
            bedrock = Bedrock("Bedrock: modelo fundacional\n+ Guardrails\n+ Knowledge Bases")
            s3 = S3("S3: documentos,\nIncidencias cerradas,\nlogs (Object Lock)")
            appcfg = SystemsManagerAppConfig("AppConfig\nreglas SLA/ruteo")

        with Cluster("Identidad, secretos y observabilidad"):
            sso = SingleSignOn("IAM Identity Center\n(administración, federado)")
            sec = SecretsManager("Secrets Manager")
            kms = KMS("KMS")
            cw = Cloudwatch("CloudWatch")
            trail = Cloudtrail("CloudTrail")

    # Ingesta y aprobaciones: ambas entran por webhook de los sistemas del operador
    mon >> Edge(label="alertas") >> dx
    tickets >> Edge(label="tickets y\naprobaciones") >> dx
    noc >> Edge(label="aprueba en el ticket") >> tickets
    dx - Edge(style="dashed") - vpn
    dx >> apigw >> cola >> pipes >> sfn

    # Orquestación
    sfn >> lam
    sfn >> Edge(label="invoca") >> agente
    sfn >> writer
    lam >> Edge(label="lectura") >> dx
    lam >> aurora
    agente >> Edge(label="MCP") >> apigw_mcp >> mcp
    mcp >> Edge(label="lectura") >> dx
    mcp >> aurora
    mcp >> Edge(label="Retrieve") >> vpce
    agente >> vpce >> bedrock
    lam >> vpce
    bedrock >> Edge(label="KB") >> aurora
    aurora >> Edge(label="export cerradas\ny revisadas", style="dashed") >> s3
    repos >> Edge(label="sync versionado", style="dashed") >> s3
    s3 >> Edge(style="dashed") >> bedrock
    lam >> Edge(style="dashed") >> appcfg

    # Única ruta de escritura
    writer >> Edge(label="nota interna / derivación", color="firebrick", penwidth="2") >> dx
