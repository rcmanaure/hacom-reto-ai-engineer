"""Diagrama de arquitectura física (AWS + on-prem).

Render: uv run --python 3.13 --with diagrams python fisica.py  (requiere Graphviz en PATH)
"""
from diagrams import Cluster, Diagram, Edge
from diagrams.aws.compute import Fargate, Lambda
from diagrams.aws.database import Aurora
from diagrams.aws.devtools import XRay
from diagrams.aws.integration import EventbridgePipes, SQS, StepFunctions
from diagrams.aws.management import Cloudtrail, Cloudwatch, SystemsManagerAppConfig
from diagrams.aws.ml import Bedrock
from diagrams.aws.network import APIGateway, DirectConnect, Endpoint, SiteToSiteVpn
from diagrams.aws.security import KMS, SecretsManager, SingleSignOn
from diagrams.aws.storage import S3
from diagrams.generic.storage import Storage
from diagrams.onprem.client import Users
from diagrams.onprem.database import PostgreSQL
from diagrams.onprem.monitoring import Zabbix
from diagrams.onprem.vcs import Git

graph_attr = {"fontsize": "14", "pad": "0.4", "nodesep": "0.45", "ranksep": "0.8", "splines": "spline"}

with Diagram("Arquitectura física", filename="fisica", outformat="png",
             direction="TB", graph_attr=graph_attr, show=False):

    with Cluster("Operador · on-prem"):
        mon = Zabbix("Monitoreo (NMS)")
        tickets = Storage("Plataforma de tickets")
        catalogo = Storage("Catálogo clientes/servicios")
        bd = PostgreSQL("BD relacional\ninventario/topología")
        repos = Git("Repos documentación")
        noc = Users("Operador NOC")

    with Cluster("Enlace privado"):
        dx = DirectConnect("Direct Connect")
        vpn = SiteToSiteVpn("VPN respaldo")

    with Cluster("AWS · región de referencia"):
        with Cluster("VPC privada (sin salida a Internet)"):
            apigw = APIGateway("API Gateway privado\nwebhooks + callback HITL")
            cola = SQS("SQS + DLQ")
            pipes = EventbridgePipes("EventBridge Pipes")
            sfn = StepFunctions("Step Functions\nStandard")
            with Cluster("Pasos deterministas"):
                lam = Lambda("Lambdas: validar,\ncorrelacionar, enriquecer,\nreglas, enmascarar PII")
                writer = Lambda("ticket-writer\n(único rol con escritura)")
            agente = Fargate("Agente de investigación\nECS Fargate")
            mcp = Lambda("Servidor MCP\nsolo lectura (IAM auth)")
            aurora = Aurora("Aurora PostgreSQL\nServerless v2\nestado + auditoría + pgvector")
            vpce = Endpoint("VPC endpoints\nBedrock, S3, Secrets")

        with Cluster("Servicios gestionados"):
            bedrock = Bedrock("Bedrock: modelo fundacional\n+ Guardrails\n+ Knowledge Bases")
            s3 = S3("S3: documentos,\nlogs de invocación\n(Object Lock)")
            appcfg = SystemsManagerAppConfig("AppConfig\nreglas SLA/ruteo")

        with Cluster("Identidad, secretos y observabilidad"):
            sso = SingleSignOn("IAM Identity Center\n(federado al IdP)")
            sec = SecretsManager("Secrets Manager")
            kms = KMS("KMS")
            cw = Cloudwatch("CloudWatch")
            xray = XRay("X-Ray")
            trail = Cloudtrail("CloudTrail")

    # Ingesta
    mon >> Edge(label="alertas") >> dx
    tickets >> Edge(label="tickets") >> dx
    dx - Edge(style="dashed") - vpn
    dx >> apigw >> cola >> pipes >> sfn

    # Orquestación
    sfn >> lam
    sfn >> Edge(label="invoca") >> agente
    sfn >> writer
    lam >> Edge(label="lectura") >> dx
    lam >> aurora
    agente >> Edge(label="MCP") >> mcp
    mcp >> Edge(label="lectura") >> dx
    mcp >> aurora
    agente >> vpce >> bedrock
    lam >> vpce
    bedrock >> Edge(label="KB") >> aurora
    repos >> Edge(label="sync versionado", style="dashed") >> s3
    s3 >> Edge(style="dashed") >> bedrock
    lam >> Edge(style="dashed") >> appcfg

    # Escritura y supervisión humana
    writer >> Edge(label="nota interna / derivación", color="firebrick", penwidth="2") >> dx
    noc >> Edge(label="aprobación (task token)") >> apigw
    sso >> Edge(style="dotted") >> noc
