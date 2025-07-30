#!/usr/bin/env python3
"""
Script to connect to Salesforce and retrieve closed opportunity details
"""

import os
import sys
import logging
from datetime import datetime
from simple_salesforce import Salesforce
from dotenv import load_dotenv
from token_manager import token_manager
from config import settings
import requests
import io
from PyPDF2 import PdfReader
from bedrock_extractor import BedrockExtractor

# Load environment variables
load_dotenv('.env')

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def connect_to_salesforce():
    """
    Connect to Salesforce using token manager with automatic refresh
    """
    print("🔌 Connecting to Salesforce using token manager...")
    
    try:
        # Try to get a fresh token using token manager
        access_token = token_manager.get_access_token()
        instance_url = token_manager.get_instance_url()
        
        if access_token and instance_url:
            try:
                sf = Salesforce(
                    instance_url=instance_url,
                    session_id=access_token
                )
                print("✅ Connected via token manager!")
                return sf
            except Exception as e:
                print(f"❌ Token manager connection failed: {e}")
                # Clear token to force refresh on next attempt
                token_manager.clear_token()
        
        # Try username/password authentication as fallback
        if settings.salesforce_username and settings.salesforce_password and settings.salesforce_security_token:
            print("🔌 Falling back to username/password authentication...")
            try:
                sf = Salesforce(
                    username=settings.salesforce_username,
                    password=settings.salesforce_password,
                    security_token=settings.salesforce_security_token,
                    domain=settings.salesforce_domain
                )
                print("✅ Connected via username/password!")
                return sf
            except Exception as e:
                print(f"❌ Username/password connection failed: {e}")
        
    except Exception as e:
        print(f"❌ Salesforce connection error: {e}")
    
    print("❌ No valid Salesforce credentials found")
    print("Please set either:")
    print("  - SALESFORCE_CONSUMER_KEY and SALESFORCE_CONSUMER_SECRET for client credentials flow")
    print("  - SALESFORCE_USERNAME, SALESFORCE_PASSWORD, and SALESFORCE_SECURITY_TOKEN")
    return None

def download_pdf_content(sf, content_document_id):
    """
    Download PDF content from Salesforce ContentDocument
    """
    try:
        # Get the ContentVersion to access the actual file content
        cv_query = f"SELECT Id, VersionData FROM ContentVersion WHERE ContentDocumentId = '{content_document_id}' AND IsLatest = true LIMIT 1"
        cv_result = sf.query(cv_query)
        
        if not cv_result['records']:
            print(f"❌ No content version found for document {content_document_id}")
            return None
            
        content_version_id = cv_result['records'][0]['Id']
        
        # Build the URL to download the file content
        instance_url = token_manager.get_instance_url()
        download_url = f"{instance_url}/services/data/v58.0/sobjects/ContentVersion/{content_version_id}/VersionData"
        
        # Get access token for authorization
        access_token = token_manager.get_access_token()
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/octet-stream'
        }
        
        # Download the file content
        response = requests.get(download_url, headers=headers)
        response.raise_for_status()
        
        return response.content
        
    except Exception as e:
        print(f"❌ Error downloading PDF content: {e}")
        return None

def extract_text_from_pdf(pdf_content):
    """
    Extract text from PDF content using PyPDF2
    """
    try:
        pdf_stream = io.BytesIO(pdf_content)
        pdf_reader = PdfReader(pdf_stream)
        
        text = ""
        for page_num, page in enumerate(pdf_reader.pages):
            try:
                page_text = page.extract_text()
                text += f"\n--- Page {page_num + 1} ---\n{page_text}"
            except Exception as page_e:
                text += f"\n--- Page {page_num + 1} (Error extracting text) ---\n"
                print(f"⚠️  Error extracting text from page {page_num + 1}: {page_e}")
        
        return text.strip()
        
    except Exception as e:
        print(f"❌ Error extracting text from PDF: {e}")
        return None

def select_opportunity_and_extract_pdf(sf, opportunities):
    """
    Allow user to select an opportunity by number and then select which PDF to extract text from
    """
    if not opportunities:
        print("No opportunities available for selection.")
        return
        
    print("\n📄 Select an opportunity to extract PDF text from:")
    print("Enter the number (1-{}): ".format(len(opportunities)), end="")
    
    try:
        selection = input().strip()
        if not selection.isdigit():
            print("❌ Please enter a valid number.")
            return
            
        opp_index = int(selection) - 1
        if opp_index < 0 or opp_index >= len(opportunities):
            print(f"❌ Please enter a number between 1 and {len(opportunities)}.")
            return
            
        selected_opp = opportunities[opp_index]
        print(f"\n📋 Selected: {selected_opp['Name']}")
        
        # Get the files for this opportunity
        content_links = selected_opp.get('ContentDocumentLinks')
        files = content_links.get('records', []) if content_links else []
        
        if not files:
            print("❌ No files found for this opportunity.")
            return
            
        # Find all PDF files
        pdf_files = []
        for file in files:
            if file['ContentDocument']['FileType'].upper() == 'PDF':
                pdf_files.append(file)
                
        if not pdf_files:
            print("❌ No PDF files found for this opportunity.")
            print(f"Available file types: {', '.join([f['ContentDocument']['FileType'] for f in files])}")
            return
            
        # If only one PDF, select it automatically
        if len(pdf_files) == 1:
            selected_pdf = pdf_files[0]
            print(f"\n📄 Found 1 PDF: {selected_pdf['ContentDocument']['Title']}")
        else:
            # Let user choose which PDF to extract
            print(f"\n📄 Found {len(pdf_files)} PDF files:")
            for i, pdf in enumerate(pdf_files, 1):
                file_size = pdf['ContentDocument']['ContentSize']
                file_size_mb = file_size / (1024 * 1024) if file_size else 0
                print(f"   {i}. {pdf['ContentDocument']['Title']} ({file_size_mb:.2f} MB)")
            
            print(f"\nSelect PDF to extract (1-{len(pdf_files)}): ", end="")
            pdf_selection = input().strip()
            
            if not pdf_selection.isdigit():
                print("❌ Please enter a valid number.")
                return
                
            pdf_index = int(pdf_selection) - 1
            if pdf_index < 0 or pdf_index >= len(pdf_files):
                print(f"❌ Please enter a number between 1 and {len(pdf_files)}.")
                return
                
            selected_pdf = pdf_files[pdf_index]
        
        print(f"\n📄 Extracting text from: {selected_pdf['ContentDocument']['Title']}")
        print("⏳ Downloading PDF content...")
        
        # Download the PDF content
        content_document_id = selected_pdf['ContentDocumentId']
            
        pdf_content = download_pdf_content(sf, content_document_id)
        
        if not pdf_content:
            print("❌ Failed to download PDF content.")
            return
            
        print("⏳ Extracting text from PDF...")
        
        # Extract text from the PDF
        extracted_text = extract_text_from_pdf(pdf_content)
        
        if not extracted_text:
            print("❌ Failed to extract text from PDF.")
            return
            
        print("\n" + "=" * 80)
        print(f"📄 TEXT CONTENT FROM: {selected_pdf['ContentDocument']['Title']}")
        print("=" * 80)
        print(extracted_text)
        print("\n" + "=" * 80)
        print(f"📊 Text extraction complete. Total characters: {len(extracted_text)}")
        
        # Ask if user wants to extract contract information using AWS Bedrock
        print("\n🤖 Would you like to extract contract information (Effective Date & Total Amount) using AI?")
        print("Enter 'y' for yes, any other key to skip: ", end="")
        extract_choice = input().strip().lower()
        
        if extract_choice == 'y':
            try:
                print("\n⏳ Analyzing contract with AWS Bedrock...")
                extractor = BedrockExtractor()
                results = extractor.extract_contract_info(extracted_text)
                formatted_results = extractor.format_results(results)
                print(formatted_results)
            except Exception as e:
                print(f"\n❌ Error using Bedrock: {e}")
                print("Please ensure AWS credentials are configured in your .env file.")
        
    except KeyboardInterrupt:
        print("\n\n👋 Operation cancelled by user.")
    except Exception as e:
        print(f"❌ Error during PDF extraction: {e}")

def get_closed_opportunities(sf, limit=10):
    """
    Query Salesforce for closed won opportunities that have files attached and display their details
    """
    print(f"\n📊 Querying for closed won opportunities with files attached (limit: {limit})...")
    
    # First, get all closed won opportunities with their file attachments
    query = f"""
    SELECT Id, Name, AccountId, Account.Name, StageName, Amount, CloseDate, 
           Type, LeadSource, Description, CreatedDate, LastModifiedDate,
           Owner.Name, Owner.Email,
           (SELECT Id, ContentDocumentId, ContentDocument.Title, ContentDocument.FileType, 
                   ContentDocument.ContentSize, ContentDocument.CreatedDate
            FROM ContentDocumentLinks
            LIMIT 5)
    FROM Opportunity 
    WHERE StageName = 'Closed Won'
    ORDER BY CloseDate DESC
    """
    
    try:
        result = sf.query(query)
        all_opportunities = result['records']
        
        # Filter to only include opportunities that have files attached
        opportunities = []
        for opp in all_opportunities:
            content_links = opp.get('ContentDocumentLinks')
            has_files = content_links and content_links.get('records')
            
            if has_files:
                opportunities.append(opp)
        
        # Limit the results to the requested number
        opportunities = opportunities[:limit]
        
        if not opportunities:
            print("No closed won opportunities with files found.")
            return
        
        print(f"\n✅ Found {len(opportunities)} closed won opportunities:\n")
        print("=" * 100)
        
        for i, opp in enumerate(opportunities, 1):
            print(f"\n{i}. Opportunity: {opp['Name']}")
            print(f"   ID: {opp['Id']}")
            print(f"   Account: {opp['Account']['Name'] if opp['Account'] else 'N/A'}")
            print(f"   Stage: {opp['StageName']}")
            print(f"   Amount: ${opp['Amount']:,.2f}" if opp['Amount'] else "   Amount: N/A")
            print(f"   Close Date: {opp['CloseDate']}")
            print(f"   Type: {opp['Type'] or 'N/A'}")
            print(f"   Lead Source: {opp['LeadSource'] or 'N/A'}")
            print(f"   Owner: {opp['Owner']['Name']} ({opp['Owner']['Email']})")
            print(f"   Created: {opp['CreatedDate']}")
            print(f"   Last Modified: {opp['LastModifiedDate']}")
            
            if opp['Description']:
                print(f"   Description: {opp['Description'][:100]}..." if len(opp['Description']) > 100 else f"   Description: {opp['Description']}")
            
            # Display attached files
            content_links = opp.get('ContentDocumentLinks')
            files = content_links.get('records', []) if content_links else []
            
            if files:
                print(f"   📎 Attached Files ({len(files)}):")
                for file in files:
                    file_size = file['ContentDocument']['ContentSize']
                    file_size_mb = file_size / (1024 * 1024) if file_size else 0
                    print(f"      • {file['ContentDocument']['Title']}")
                    print(f"        Type: {file['ContentDocument']['FileType']}")
                    print(f"        Size: {file_size_mb:.2f} MB")
                    print(f"        Created: {file['ContentDocument']['CreatedDate']}")
            else:
                print(f"   📎 No files attached")
            
            print("-" * 100)
        
        # Summary statistics
        total_amount = sum(opp['Amount'] or 0 for opp in opportunities)
        total_files = 0
        opps_with_files = 0
        for opp in opportunities:
            content_links = opp.get('ContentDocumentLinks')
            if content_links and content_links.get('records'):
                files = content_links.get('records', [])
                total_files += len(files)
                opps_with_files += 1
        
        print(f"\n📈 Summary:")
        print(f"   Total Opportunities: {len(opportunities)}")
        print(f"   Total Amount: ${total_amount:,.2f}")
        print(f"   Opportunities with Files: {opps_with_files}")
        print(f"   Total Files Attached: {total_files}")
        
        # Get won vs lost breakdown
        won_opps = [opp for opp in opportunities if 'won' in opp['StageName'].lower()]
        lost_opps = [opp for opp in opportunities if 'lost' in opp['StageName'].lower()]
        
        print(f"   Won: {len(won_opps)}")
        print(f"   Lost: {len(lost_opps)}")
        print(f"   Other: {len(opportunities) - len(won_opps) - len(lost_opps)}")
        
        return opportunities
        
    except Exception as e:
        print(f"❌ Error querying opportunities: {e}")
        return []

def debug_specific_opportunity(sf, opp_name):
    """
    Debug a specific opportunity to see its stage and attachments
    """
    print(f"\n🔍 Searching for opportunity: '{opp_name}'")
    
    # First search for the opportunity without attachments
    basic_query = f"""
    SELECT Id, Name, StageName, Amount, CloseDate, 
           (SELECT Id, ContentDocumentId, ContentDocument.Title, ContentDocument.FileType 
            FROM ContentDocumentLinks LIMIT 10)
    FROM Opportunity 
    WHERE Name LIKE '%{opp_name}%'
    LIMIT 10
    """
    
    try:
        result = sf.query(basic_query)
        opportunities = result['records']
        
        if not opportunities:
            print(f"❌ No opportunities found matching '{opp_name}'")
            return
            
        for opp in opportunities:
            print(f"\n✅ Found: {opp['Name']}")
            print(f"   Stage: {opp['StageName']}")
            print(f"   Amount: ${opp['Amount']:,.2f}" if opp['Amount'] else "   Amount: N/A")
            print(f"   Close Date: {opp['CloseDate']}")
            
            # Check ContentDocumentLinks (Files)
            content_links = opp.get('ContentDocumentLinks')
            files = content_links.get('records', []) if content_links else []
            if files:
                print(f"   📎 Files ({len(files)}):")
                for file in files:
                    print(f"      • {file['ContentDocument']['Title']} ({file['ContentDocument']['FileType']})")
            else:
                print(f"   📎 No Files found")
            
            # Check legacy Attachments separately (without Body field)
            try:
                att_query = f"SELECT Id, Name, ContentType FROM Attachment WHERE ParentId = '{opp['Id']}' LIMIT 10"
                att_result = sf.query(att_query)
                atts = att_result['records']
                if atts:
                    print(f"   📎 Attachments ({len(atts)}):")
                    for att in atts:
                        print(f"      • {att['Name']} ({att['ContentType']})")
                else:
                    print(f"   📎 No Attachments found")
            except Exception as att_e:
                print(f"   📎 Error checking attachments: {att_e}")
                
    except Exception as e:
        print(f"❌ Error searching: {e}")

def main():
    """
    Main function to run the script
    """
    print("🚀 Salesforce Closed Won Opportunities Retrieval Script")
    print("=" * 50)
    
    # Connect to Salesforce
    sf = connect_to_salesforce()
    if not sf:
        sys.exit(1)
    
    # Get closed opportunities
    opportunities = get_closed_opportunities(sf, limit=20)
    
    # Allow user to select an opportunity and extract PDF text
    if opportunities:
        select_opportunity_and_extract_pdf(sf, opportunities)
    

if __name__ == "__main__":
    main()