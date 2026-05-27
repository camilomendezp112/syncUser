import json
import os
import boto3
from datetime import datetime

# Initialize DynamoDB resources
dynamodb = boto3.resource('dynamodb')
TABLE_NAME = os.environ.get('TABLE_NAME')
table = dynamodb.Table(TABLE_NAME)

# Safely check if sentry_sdk is available in the Lambda environment
try:
    import sentry_sdk
    HAS_SENTRY = True
except ImportError:
    HAS_SENTRY = False
    print("sentry_sdk package not found. Skipping Sentry integration.")

# Safely initialize Sentry if available and configured
if HAS_SENTRY:
    sentry_dsn = os.environ.get("SENTRY_DSN")
    if sentry_dsn:
        try:
            sentry_sdk.init(
                dsn=sentry_dsn,
                traces_sample_rate=1.0
            )
            sentry_sdk.set_tag("module", "syncUser")
            sentry_sdk.set_tag("team", "grupo-3")
        except Exception as e:
            print(f"Error initializing Sentry: {str(e)}")

def lambda_handler(event, context):
    """
    This Lambda function serves a dual purpose:
    1. Cognito Post Confirmation Trigger: Automatically registers new users after Cognito verification.
    2. API Gateway Endpoint (HTTP POST): Direct creation/synchronization of users (e.g. from Swagger Studio).
    """
    # Detect Cognito event structure
    is_cognito = isinstance(event, dict) and 'request' in event and 'userAttributes' in event['request']
    
    if is_cognito:
        try:
            # Extract user attributes from Cognito event
            user_attributes = event.get('request', {}).get('userAttributes', {})
            sub = user_attributes.get('sub')
            email = user_attributes.get('email')
            tenant_id = "Ecommerce00"
            
            if not sub:
                print("Missing required attribute (sub). Skipping DynamoDB write.")
                return event
                
            created_at = datetime.utcnow().isoformat()
            
            item = {
                'PK': f"USER#{sub}",
                'SK': f"TENANT#{tenant_id}",
                'id': sub,
                'email': email,
                'tenant_id': tenant_id,
                'status': 'CONFIRMED',
                'created_at': created_at
            }
            
            table.put_item(Item=item)
            print(f"Successfully saved user {sub} for tenant {tenant_id} (Cognito Flow)")
            
        except Exception as e:
            # Do not fail the Cognito flow if DynamoDB write fails, but log it
            print(f"Error writing user to DynamoDB in Cognito flow: {str(e)}")
            
        return event

    else:
        # HTTP / API Gateway Flow
        try:
            # Parse request body from API Gateway proxy or direct invocation
            body = {}
            if isinstance(event, dict):
                if 'body' in event and event['body'] is not None:
                    try:
                        body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
                    except Exception:
                        body = event
                else:
                    body = event
            else:
                body = {}
            
            # Extract key fields for user creation/sync
            sub = body.get('user_id') or body.get('sub') or body.get('id')
            email = body.get('email')
            tenant_id = "Ecommerce00"
            
            if not sub:
                error_msg = "Missing required field. 'user_id' (or 'sub') is required."
                print(error_msg)
                return {
                    "statusCode": 400,
                    "headers": {
                        "Content-Type": "application/json",
                        "Access-Control-Allow-Origin": "*"
                    },
                    "body": json.dumps({"error": error_msg})
                }
            
            created_at = datetime.utcnow().isoformat()
            
            item = {
                'PK': f"USER#{sub}",
                'SK': f"TENANT#{tenant_id}",
                'id': sub,
                'email': email or "",
                'tenant_id': tenant_id,
                'status': 'CONFIRMED',
                'created_at': created_at
            }
            
            table.put_item(Item=item)
            print(f"Successfully saved user {sub} for tenant {tenant_id} (API Flow)")
            
            return {
                "statusCode": 201,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({
                    "message": "User created/synchronized successfully",
                    "user": {
                        "id": sub,
                        "email": email or "",
                        "tenant_id": tenant_id,
                        "status": "CONFIRMED",
                        "created_at": created_at
                    }
                })
            }
            
        except Exception as e:
            error_msg = f"Error writing user to DynamoDB: {str(e)}"
            print(error_msg)
            return {
                "statusCode": 500,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({"error": error_msg})
            }
