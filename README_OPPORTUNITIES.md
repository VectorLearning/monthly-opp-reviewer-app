# Salesforce Closed Opportunities Retrieval Script with AI Contract Analysis

This script connects to your Salesforce instance and retrieves details about closed opportunities with file attachments. It now includes the ability to extract contract information (Effective Date and Total Amount) from PDF attachments using AWS Bedrock AI.

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Salesforce credentials:**
   
   Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
   
   Then edit `.env` with your Salesforce credentials. You have two authentication options:

   **Option 1: OAuth2 (Recommended)**
   - Set `SALESFORCE_ACCESS_TOKEN` and `SALESFORCE_INSTANCE_URL`
   - You can get these from the existing app's OAuth flow or from Salesforce Setup

   **Option 2: Username/Password**
   - Set `SALESFORCE_USERNAME`, `SALESFORCE_PASSWORD`, and `SALESFORCE_SECURITY_TOKEN`
   - Get your security token from Salesforce: Setup → Personal Setup → My Personal Information → Reset My Security Token

3. **Configure AWS Bedrock credentials (for AI contract analysis):**
   
   Add these to your `.env` file:
   ```
   aws_access_key_id=your_aws_access_key_here
   aws_secret_access_key=your_aws_secret_key_here
   aws_session_token=your_session_token_here  # Optional, only if using temporary credentials
   AWS_REGION=us-east-1
   BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
   ```
   
   Note: 
   - AWS credentials are required only if you want to use the AI contract analysis feature
   - The session token is only needed if you're using temporary AWS credentials
   - The credentials can be in lowercase (as shown) or uppercase format
   - The AI sends the raw PDF file to Bedrock using the "image" type with "application/pdf" media type
   - Claude 3 models are required (Claude 2 doesn't support multimodal inputs)

## Usage

Run the script:
```bash
python get_closed_opportunities.py
```

The script will:
1. Connect to your Salesforce instance
2. Query for closed won opportunities that have file attachments
3. Display detailed information including:
   - Opportunity name and ID
   - Account name
   - Stage (Closed Won)
   - Amount
   - Close date
   - Type and lead source
   - Owner information
   - Description (truncated if long)
   - Attached files with metadata
4. Show summary statistics (total count, total amount, file count breakdown)
5. Allow you to select an opportunity and extract text from its PDF attachments
6. **NEW**: Optionally use AWS Bedrock AI to analyze the PDF and extract:
   - Effective Date of the contract
   - Total Amount from the contract
   - Confidence scores for each extraction
   - Note: The AI converts PDF pages to images for analysis, preserving formatting and layout

## What the Script Shows

For each closed opportunity with files, you'll see:
- Basic information (name, account, stage)
- Financial details (amount)
- Timeline (close date, created date, last modified)
- Source information (type, lead source)
- Owner details (name and email)
- Description (if available)
- Attached files with:
  - File name and type
  - File size
  - Creation date

When extracting PDF content with AI, you'll see:
- Effective Date (if found in the contract)
- Total Amount (if found in the contract)
- Confidence scores for each extraction
- Notes about where the information was found

## Customization

You can modify the script to:
- Change the number of opportunities retrieved (modify the `limit` parameter)
- Add additional fields to the query
- Filter by specific date ranges
- Export results to CSV or Excel
- Filter by specific stages or criteria

## Troubleshooting

1. **Authentication errors:**
   - Verify your credentials in the `.env` file
   - For sandbox, use `SALESFORCE_DOMAIN=test`
   - For production, use `SALESFORCE_DOMAIN=login`

2. **Field access errors:**
   - Ensure your Salesforce user has permission to view Opportunities
   - Check that all queried fields are accessible to your profile

3. **No opportunities found:**
   - Verify that closed opportunities exist in your Salesforce instance
   - Check that your user has visibility to the opportunities