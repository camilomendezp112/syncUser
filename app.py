import json
import os
import boto3
import sentry_sdk
import os
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
TABLE_NAME = os.environ.get('TABLE_NAME')
table = dynamodb.Table(TABLE_NAME)

sentry_sdk.init(
    dsn=os.environ["SENTRY_DSN"],
    traces_sample_rate=1.0
)

sentry_sdk.set_tag("module", "manageAsset")
sentry_sdk.set_tag("team", "grupo-3")

def lambda_handler(event, context):
    """
    This Lambda acts as a Cognito Post Confirmation trigger.
    It writes the newly confirmed user into DynamoDB.
    """
    try:
        # Extract user attributes from Cognito event
        user_attributes = event.get('request', {}).get('userAttributes', {})
        sub = user_attributes.get('sub')
        email = user_attributes.get('email')
        tenant_id = user_attributes.get('custom:tenant_id')
        
        if not sub or not tenant_id:
            print("Missing required attributes (sub or custom:tenant_id). Skipping DynamoDB write.")
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
        print(f"Successfully saved user {sub} for tenant {tenant_id}")
        
    except Exception as e:
        # Do not fail the Cognito flow if DynamoDB write fails
        # but log the error for monitoring.
        print(f"Error writing user to DynamoDB: {str(e)}")
        
    # Return the event to Cognito to complete the flow
    return event
