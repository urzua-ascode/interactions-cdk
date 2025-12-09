import json
import os
import boto3
from boto3.dynamodb.conditions import Key

# Inicialización fuera del handler para optimizar "cold starts"
dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('TABLE_NAME')
table = dynamodb.Table(table_name)

def main(event, context):
    print("Request:", json.dumps(event))

    # Ruta esperada: /interactions/{account_number}
    path = event.get('path', '')
    
    # Extracción muy simple del account_number desde la URL
    # Asumimos formato /interactions/123456
    try:
        parts = path.strip('/').split('/')
        if len(parts) < 2 or parts[0] != 'interactions':
             return {'statusCode': 400, 'body': json.dumps({'error': 'Ruta invalida'})}
        
        account_number = parts[1]

        # Consulta a DynamoDB
        response = table.query(
            KeyConditionExpression=Key('account_number').eq(account_number)
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'account_number': account_number,
                'items': response.get('Items', []),
                'count': response.get('Count', 0)
            })
        }
    except Exception as e:
        print(e)
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}