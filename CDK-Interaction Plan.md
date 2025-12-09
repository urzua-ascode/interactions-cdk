### ---

**1\. Prerrequisitos (Setup Inicial)**

Asegúrate de tener esto listo en tu terminal antes de empezar:

* **AWS CLI configurado:** Ejecuta aws configure y pon tus credenciales.  
* **Node.js:** Necesario para el núcleo de CDK.  
* **CDK CLI:** Instálalo globalmente: npm install \-g aws-cdk.

### **2\. Inicialización del Proyecto**

Vamos a crear una estructura limpia desde cero.

1. Abre tu terminal y crea una carpeta separada de tu proyecto Docker anterior:  
   Bash  
   mkdir interactions-cdk  
   cd interactions-cdk

2. Inicializa la aplicación CDK usando Python:  
   Bash  
   cdk init app \--language python

3. Activa el entorno virtual (esto aísla tus librerías):  
   Bash  
   source .venv/bin/activate

4. Instala las dependencias necesarias (incluyendo pytest para las pruebas):  
   Abre el archivo requirements.txt que se creó y asegura que tenga este contenido:  
   Plaintext  
   aws-cdk-lib==2.100.0  \# O una versión reciente  
   constructs\>=10.0.0  
   pytest  
   boto3

   Luego instala:  
   Bash  
   pip install \-r requirements.txt

### ---

**3\. El Código de Infraestructura (Stack)**

Aquí definimos los recursos mínimos: **DynamoDB** (modo bajo demanda para no pagar por servidores inactivos 2), **Lambda** y **API Gateway**.

1. Abre la carpeta interactions\_cdk (el nombre puede variar ligeramente según cómo CDK nombró la carpeta interna) y busca el archivo interactions\_cdk\_stack.py.  
2. Reemplaza todo el contenido con este código:

Python

from aws\_cdk import (  
    Stack,  
    RemovalPolicy,  
    aws\_dynamodb as dynamodb,  
    aws\_lambda as \_lambda,  
    aws\_apigateway as apigw,  
)  
from constructs import Construct

class InteractionsCdkStack(Stack):

    def \_\_init\_\_(self, scope: Construct, construct\_id: str, \*\*kwargs) \-\> None:  
        super().\_\_init\_\_(scope, construct\_id, \*\*kwargs)

        \# 1\. DynamoDB: Económica y escalable \[cite: 18, 59\]  
        table \= dynamodb.Table(  
            self, "InteractionsTable",  
            partition\_key=dynamodb.Attribute(  
                name="account\_number",   
                type\=dynamodb.AttributeType.STRING  
            ),  
            sort\_key=dynamodb.Attribute( \# Sort key para historial \[cite: 63\]  
                name="timestamp",  
                type\=dynamodb.AttributeType.STRING  
            ),  
            billing\_mode=dynamodb.BillingMode.PAY\_PER\_REQUEST, \# Costo CERO si no se usa   
            removal\_policy=RemovalPolicy.DESTROY \# Limpieza automática al destruir el stack  
        )

        \# 2\. Lambda: Lógica del negocio  
        handler \= \_lambda.Function(  
            self, "InteractionsHandler",  
            runtime=\_lambda.Runtime.PYTHON\_3\_9,  
            architecture=\_lambda.Architecture.ARM\_64, \# Más barato y rápido (Graviton)  
            code=\_lambda.Code.from\_asset("lambda"),   \# Carpeta del código  
            handler="handler.main",  
            environment={  
                "TABLE\_NAME": table.table\_name  
            }  
        )

        \# Permisos mínimos: Lambda solo puede LEER de esta tabla  
        table.grant\_read\_data(handler)

        \# 3\. API Gateway: Exposición pública \[cite: 74\]  
        api \= apigw.LambdaRestApi(  
            self, "InteractionsApi",  
            handler=handler,  
            description="API Serverless para historial de interacciones",  
            proxy=True  
        )

### ---

**4\. El Código de la Función (Lambda)**

1. En la raíz del proyecto (al mismo nivel que app.py), crea una carpeta llamada lambda.  
2. Dentro, crea un archivo handler.py.  
3. Pega este código (lógica para leer DynamoDB y responder JSON):

Python

import json  
import os  
import boto3  
from boto3.dynamodb.conditions import Key

\# Inicialización fuera del handler para optimizar "cold starts"  
dynamodb \= boto3.resource('dynamodb')  
table\_name \= os.environ.get('TABLE\_NAME')  
table \= dynamodb.Table(table\_name)

def main(event, context):  
    print("Request:", json.dumps(event))

    \# Ruta esperada: /interactions/{account\_number}  
    path \= event.get('path', '')  
      
    \# Extracción muy simple del account\_number desde la URL  
    \# Asumimos formato /interactions/123456  
    try:  
        parts \= path.strip('/').split('/')  
        if len(parts) \< 2 or parts\[0\] \!= 'interactions':  
             return {'statusCode': 400, 'body': json.dumps({'error': 'Ruta invalida'})}  
          
        account\_number \= parts\[1\]

        \# Consulta a DynamoDB  
        response \= table.query(  
            KeyConditionExpression=Key('account\_number').eq(account\_number)  
        )  
          
        return {  
            'statusCode': 200,  
            'body': json.dumps({  
                'account\_number': account\_number,  
                'items': response.get('Items', \[\]),  
                'count': response.get('Count', 0)  
            })  
        }  
    except Exception as e:  
        print(e)  
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}

### ---

**5\. Pruebas de Infraestructura (Unit Tests)**

Esto es lo que diferencia a un Junior de un Senior. Vamos a probar que nuestro código CDK realmente genera la infraestructura correcta *antes* de desplegar.

1. Ve a la carpeta tests/unit (CDK la crea automáticamente).  
2. Abre test\_interactions\_cdk\_stack.py y reemplázalo con esto:

Python

import aws\_cdk as core  
import aws\_cdk.assertions as assertions  
from interactions\_cdk.interactions\_cdk\_stack import InteractionsCdkStack

\# Test: Verificar que se crea la tabla DynamoDB con la configuración correcta  
def test\_dynamodb\_created():  
    app \= core.App()  
    stack \= InteractionsCdkStack(app, "interactions-cdk")  
    template \= assertions.Template.from\_stack(stack)

    \# Verificar que existe un recurso AWS::DynamoDB::Table  
    template.resource\_count\_is("AWS::DynamoDB::Table", 1)

    \# Verificar propiedades específicas (Partition Key y Billing Mode)  
    template.has\_resource\_properties("AWS::DynamoDB::Table", {  
        "KeySchema": \[  
            {"AttributeName": "account\_number", "KeyType": "HASH"},  
            {"AttributeName": "timestamp", "KeyType": "RANGE"}  
        \],  
        "BillingMode": "PAY\_PER\_REQUEST"  
    })

\# Test: Verificar que existe la función Lambda  
def test\_lambda\_created():  
    app \= core.App()  
    stack \= InteractionsCdkStack(app, "interactions-cdk")  
    template \= assertions.Template.from\_stack(stack)  
      
    template.resource\_count\_is("AWS::Lambda::Function", 1)

3. Ejecutar las pruebas:  
   En la terminal, corre:  
   Bash  
   pytest

   *Deberías ver letras verdes indicando que los tests pasaron.*

### ---

**6\. Despliegue (Deployment)**

Una vez que los tests pasaron, vamos a subir esto a AWS.

1. Bootstrap (Solo la primera vez):  
   Prepara tu cuenta AWS para usar CDK (crea un bucket S3 interno para guardar los archivos).  
   Bash  
   cdk bootstrap

2. Sintetizar (Opcional pero recomendado):  
   Genera la plantilla CloudFormation localmente para verificar.  
   Bash  
   cdk synth

3. Desplegar:  
   Crea los recursos en la nube.  
   Bash  
   cdk deploy

   *Te pedirá confirmación (y/n). Escribe y y presiona Enter.*

### **7\. Verificación Final**

Cuando termine el despliegue, la terminal te mostrará algo llamado **"Outputs"**. Busca una URL que termina en ...amazonws.com/prod/. Esa es tu API.

Prueba con curl:  
Usa esa URL y agrega /interactions/12345 al final.

Bash

curl https://xxxxxx.execute-api.us-east-1.amazonaws.com/prod/interactions/12345

*(Inicialmente devolverá una lista vacía \[\] porque la tabla DynamoDB está vacía, pero confirmará que toda la cadena API \-\> Lambda \-\> DB funciona).*

### ---

**8\. Limpieza (Importante)**

Para evitar cualquier costo futuro o dejar "basura" en tu cuenta, destruye todo cuando termines la demo:

Bash

cdk destroy

### **Resumen para tu entrevista**

Con esto has demostrado:

1. **Serverless First:** Usaste componentes que escalan a cero (costo cero).  
2. **IaC:** Todo es código, reproducible y versionable.  
3. **Quality Assurance:** Incluiste pruebas unitarias de infraestructura.  
4. **Seguridad:** Aplicaste el principio de privilegio mínimo en los permisos IAM.