# Salesforce Closed Opportunities Retrieval Script

This script connects to your Salesforce instance and retrieves details about closed opportunities.

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

## Usage

Run the script:
```bash
python get_closed_opportunities.py
```

The script will:
1. Connect to your Salesforce instance
2. Query for the 20 most recently closed opportunities
3. Display detailed information including:
   - Opportunity name and ID
   - Account name
   - Stage (Closed Won, Closed Lost, etc.)
   - Amount
   - Close date
   - Type and lead source
   - Owner information
   - Description (truncated if long)
4. Show summary statistics (total count, total amount, won/lost breakdown)
5. Optionally let you search for specific opportunities by name

## What the Script Shows

For each closed opportunity, you'll see:
- Basic information (name, account, stage)
- Financial details (amount)
- Timeline (close date, created date, last modified)
- Source information (type, lead source)
- Owner details (name and email)
- Description (if available)

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