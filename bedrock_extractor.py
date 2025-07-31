#!/usr/bin/env python3
"""
AWS Bedrock integration for extracting contract information from PDFs
"""

import os
import json
import logging
import boto3
from botocore.config import Config
from config import settings

logger = logging.getLogger(__name__)

class BedrockExtractor:
    def __init__(self):
        """Initialize AWS Bedrock client"""
        self.aws_access_key = settings.aws_access_key_id or os.getenv('AWS_ACCESS_KEY_ID')
        self.aws_secret_key = settings.aws_secret_access_key or os.getenv('AWS_SECRET_ACCESS_KEY')
        self.aws_session_token = settings.aws_session_token or os.getenv('AWS_SESSION_TOKEN')
        self.aws_region = settings.aws_region
        self.model_id = settings.bedrock_model_id
        
        if not self.aws_access_key or not self.aws_secret_key:
            raise ValueError("AWS credentials not found in environment variables")
        
        # Configure boto3 client
        config = Config(
            region_name=self.aws_region,
            signature_version='v4',
            retries={
                'max_attempts': 3,
                'mode': 'standard'
            }
        )
        
        # Create client with or without session token
        client_params = {
            'service_name': 'bedrock-runtime',
            'aws_access_key_id': self.aws_access_key,
            'aws_secret_access_key': self.aws_secret_key,
            'config': config
        }
        
        if self.aws_session_token:
            client_params['aws_session_token'] = self.aws_session_token
            
        self.bedrock_client = boto3.client(**client_params)
        
    def extract_contract_info(self, pdf_content):
        """
        Extract effective date and total amount from contract PDF using AWS Bedrock Converse API
        
        Args:
            pdf_content (bytes): The raw PDF content
            
        Returns:
            dict: Contains 'effective_date' and 'total_amount' if found
        """
        
        logger.info("Sending PDF to AWS Bedrock for analysis...")
        
        # Craft the prompt for Claude
        prompt = """You are analyzing a contract document. Please extract the following information:

1. Effective Date: The date when the contract becomes effective or starts. This might be labeled as "Effective Date", "Start Date", "Commencement Date", or similar.
2. Total Amount: The total dollar amount of the contract. This might be labeled as "Total Contract Value", "Total Amount", "Contract Price", "Total Fee", or similar.

Please respond with a JSON object containing:
- "effective_date": The effective date in ISO format (YYYY-MM-DD) if found, or null if not found
- "total_amount": The total dollar amount as a number (without currency symbols or commas) if found, or null if not found
- "confidence": A confidence score from 0-1 for each extraction
- "notes": Any relevant notes about the extraction

Example response:
{
    "effective_date": "2024-01-15",
    "effective_date_confidence": 0.95,
    "total_amount": 150000.00,
    "total_amount_confidence": 0.90,
    "notes": "Effective date found in Section 1. Total amount calculated from monthly fees in Schedule A."
}"""

        try:
            # Construct conversation with PDF document for Converse API
            conversation = [
                {
                    "role": "user",
                    "content": [
                        {"text": prompt},
                        {
                            "document": {
                                "format": "pdf",
                                "name": "contract",
                                "source": {"bytes": pdf_content}
                            }
                        }
                    ]
                }
            ]
            
            # Use the Converse API which supports PDF documents
            response = self.bedrock_client.converse(
                modelId=self.model_id,
                messages=conversation,
                inferenceConfig={
                    "maxTokens": 1000,
                    "temperature": 0.0,
                    "topP": 0.9
                }
            )
            
            # Extract the text response from Converse API
            response_text = response["output"]["message"]["content"][0]["text"]
            
            # Try to parse the JSON response
            try:
                # Find JSON object in the response
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                if start_idx != -1 and end_idx > start_idx:
                    json_str = response_text[start_idx:end_idx]
                    result = json.loads(json_str)
                    return result
                else:
                    logger.error("No JSON object found in response")
                    return {
                        "effective_date": None,
                        "total_amount": None,
                        "error": "Could not parse response"
                    }
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.debug(f"Raw response: {response_text}")
                return {
                    "effective_date": None,
                    "total_amount": None,
                    "error": f"JSON parsing error: {str(e)}",
                    "raw_response": response_text
                }
                
        except Exception as e:
            logger.error(f"Error calling Bedrock: {e}")
            return {
                "effective_date": None,
                "total_amount": None,
                "error": f"Bedrock API error: {str(e)}"
            }
    
    def format_results(self, results):
        """
        Format the extraction results for display
        
        Args:
            results (dict): The extraction results
            
        Returns:
            str: Formatted string for display
        """
        output = "\n🤖 CONTRACT INFORMATION EXTRACTED:\n"
        output += "=" * 50 + "\n"
        
        if results.get('error'):
            output += f"❌ Error: {results['error']}\n"
            if results.get('raw_response'):
                output += f"\nRaw response:\n{results['raw_response']}\n"
        else:
            if results.get('effective_date'):
                confidence = results.get('effective_date_confidence', 0)
                output += f"📅 Effective Date: {results['effective_date']} (Confidence: {confidence:.0%})\n"
            else:
                output += "📅 Effective Date: Not found\n"
                
            if results.get('total_amount') is not None:
                confidence = results.get('total_amount_confidence', 0)
                amount = f"${results['total_amount']:,.2f}"
                output += f"💰 Total Amount: {amount} (Confidence: {confidence:.0%})\n"
            else:
                output += "💰 Total Amount: Not found\n"
                
            if results.get('notes'):
                output += f"\n📝 Notes: {results['notes']}\n"
        
        output += "=" * 50 + "\n"
        return output