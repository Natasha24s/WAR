# lambda_function.py

import json
import boto3
import base64
import logging
from botocore.config import Config
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Create Bedrock Runtime client with increased timeout
bedrock_runtime = boto3.client(
    service_name='bedrock-runtime',
    config=Config(read_timeout=300)
)

def analyze_architecture(image_base64):
    try:
        model_input = {
            "schemaVersion": "messages-v1",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "image": {
                                "format": "jpeg",
                                "source": {"bytes": image_base64}
                            }
                        },
                        {
                            "text": """Please analyze this AWS architecture diagram and provide a detailed assessment following the AWS Well-Architected Framework's six pillars.

For each pillar (Operational Excellence, Security, Reliability, Performance Efficiency, Cost Optimization, and Sustainability), provide:
1. Identified strengths in the architecture
2. Potential risks or gaps
3. Risk level (High/Medium/Low)
4. Specific recommendations for improvement

Format your response exactly as follows for each pillar:
| Pillar | Strengths | Risks | Risk Level | Recommendations |
Include concrete details and specific AWS services in your analysis."""
                        }
                    ]
                }
            ],
            "system": [
                {
                    "text": "You are an AWS Well-Architected Framework expert system. Analyze architecture diagrams thoroughly and provide detailed assessments with specific, actionable recommendations."
                }
            ],
            "inferenceConfig": {
                "maxTokens": 2048,
                "temperature": 0.7,
                "topP": 0.8,
                "stopSequences": []
            }
        }

        logger.info("Calling Bedrock with model input")
        response = bedrock_runtime.invoke_model(
            modelId="amazon.nova-lite-v1:0",
            body=json.dumps(model_input)
        )
        
        model_response = json.loads(response["body"].read())
        logger.info(f"Raw model response: {json.dumps(model_response)}")
        
        # Extract the text response
        if "output" in model_response and "message" in model_response["output"]:
            analysis_text = model_response["output"]["message"]["content"][0]["text"]
            logger.info(f"Analysis text: {analysis_text}")
            return analysis_text
        else:
            logger.error("Unexpected response format")
            raise Exception("Unexpected response format from model")
        
    except Exception as e:
        logger.error(f"Error analyzing architecture: {str(e)}")
        raise

def lambda_handler(event, context):
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'OPTIONS,POST'
    }
    
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }
        
    try:
        body = json.loads(event['body'])
        image_base64 = body.get('image')
        
        if not image_base64:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Image data is required'})
            }
            
        analysis_result = analyze_architecture(image_base64)
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'analysis': analysis_result,
                'raw_response': True  # Adding this flag for debugging
            })
        }
            
    except Exception as e:
        logger.error(f"Lambda handler error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }
