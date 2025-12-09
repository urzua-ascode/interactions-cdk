import aws_cdk as core
import aws_cdk.assertions as assertions
from interactions_cdk.interactions_cdk_stack import InteractionsCdkStack

# Test: Verificar que se crea la tabla DynamoDB con la configuración correcta
def test_dynamodb_created():
    app = core.App()
    stack = InteractionsCdkStack(app, "interactions-cdk")
    template = assertions.Template.from_stack(stack)

    # Verificar que existe un recurso AWS::DynamoDB::Table
    template.resource_count_is("AWS::DynamoDB::Table", 1)

    # Verificar propiedades específicas (Partition Key y Billing Mode)
    template.has_resource_properties("AWS::DynamoDB::Table", {
        "KeySchema": [
            {"AttributeName": "account_number", "KeyType": "HASH"},
            {"AttributeName": "timestamp", "KeyType": "RANGE"}
        ],
        "BillingMode": "PAY_PER_REQUEST"
    })

# Test: Verificar que existe la función Lambda
def test_lambda_created():
    app = core.App()
    stack = InteractionsCdkStack(app, "interactions-cdk")
    template = assertions.Template.from_stack(stack)
    
    template.resource_count_is("AWS::Lambda::Function", 1)