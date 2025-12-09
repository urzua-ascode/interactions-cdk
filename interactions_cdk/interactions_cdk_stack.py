from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_dynamodb as dynamodb,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
)
from constructs import Construct

class InteractionsCdkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. DynamoDB: Económica y escalable [cite: 18, 59]
        table = dynamodb.Table(
            self, "InteractionsTable",
            partition_key=dynamodb.Attribute(
                name="account_number", 
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute( # Sort key para historial [cite: 63]
                name="timestamp",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST, # Costo CERO si no se usa 
            removal_policy=RemovalPolicy.DESTROY # Limpieza automática al destruir el stack
        )

        # 2. Lambda: Lógica del negocio
        handler = _lambda.Function(
            self, "InteractionsHandler",
            runtime=_lambda.Runtime.PYTHON_3_9,
            architecture=_lambda.Architecture.ARM_64, # Más barato y rápido (Graviton)
            code=_lambda.Code.from_asset("lambda"),   # Carpeta del código
            handler="handler.main",
            environment={
                "TABLE_NAME": table.table_name
            }
        )

        # Permisos mínimos: Lambda solo puede LEER de esta tabla
        table.grant_read_data(handler)

        # 3. API Gateway: Exposición pública [cite: 74]
        api = apigw.LambdaRestApi(
            self, "InteractionsApi",
            handler=handler,
            description="API Serverless para historial de interacciones",
            proxy=True
        )