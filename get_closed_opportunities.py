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
           (SELECT Id, ContentDocument.Title, ContentDocument.FileType, 
                   ContentDocument.ContentSize, ContentDocument.CreatedDate
            FROM ContentDocumentLinks
            LIMIT 5)
    FROM Opportunity 
    WHERE StageName = 'Closed Won'
    ORDER BY CloseDate DESC 
    LIMIT 500
    """
    
    try:
        result = sf.query(query)
        all_opportunities = result['records']
        
        print(f"📋 Debug: Found {len(all_opportunities)} total closed won opportunities")
        
        # Filter to only include opportunities that have files attached
        opportunities = []
        opportunities_without_files = []
        
        for opp in all_opportunities:
            content_links = opp.get('ContentDocumentLinks')
            has_files = content_links and content_links.get('records')
            
            # Also check for legacy attachments
            has_attachments = False
            try:
                att_query = f"SELECT Id FROM Attachment WHERE ParentId = '{opp['Id']}' LIMIT 1"
                att_result = sf.query(att_query)
                has_attachments = len(att_result['records']) > 0
            except:
                pass
            
            if has_files or has_attachments:
                opportunities.append(opp)
                attachment_type = "Files" if has_files else "Attachments"
                print(f"✅ HAS {attachment_type}: {opp['Name']}")
            else:
                opportunities_without_files.append(opp)
                print(f"❌ NO FILES: {opp['Name']}")
        
        print(f"\n📊 Summary: {len(opportunities)} with files, {len(opportunities_without_files)} without files")
        
        # Limit the results to the requested number
        opportunities = opportunities[:limit]
        
        if not opportunities:
            print("No closed won opportunities with files found.")
            print("Showing first 5 opportunities without files for reference:")
            for i, opp in enumerate(opportunities_without_files[:5], 1):
                print(f"  {i}. {opp['Name']} - {opp['CloseDate']}")
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
            
            # Also check for legacy attachments
            attachments = []
            try:
                att_query = f"SELECT Id, Name, ContentType FROM Attachment WHERE ParentId = '{opp['Id']}'"
                att_result = sf.query(att_query)
                attachments = att_result['records']
            except:
                pass
            
            if files:
                print(f"   📎 Attached Files ({len(files)}):")
                for file in files:
                    file_size = file['ContentDocument']['ContentSize']
                    file_size_mb = file_size / (1024 * 1024) if file_size else 0
                    print(f"      • {file['ContentDocument']['Title']}")
                    print(f"        Type: {file['ContentDocument']['FileType']}")
                    print(f"        Size: {file_size_mb:.2f} MB")
                    print(f"        Created: {file['ContentDocument']['CreatedDate']}")
            
            if attachments:
                print(f"   📎 Legacy Attachments ({len(attachments)}):")
                for att in attachments:
                    print(f"      • {att['Name']} ({att['ContentType']})")
            
            if not files and not attachments:
                print(f"   📎 No files or attachments")
            
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
        
    except Exception as e:
        print(f"❌ Error querying opportunities: {e}")
        return

def debug_specific_opportunity(sf, opp_name):
    """
    Debug a specific opportunity to see its stage and attachments
    """
    print(f"\n🔍 Searching for opportunity: '{opp_name}'")
    
    # First search for the opportunity without attachments
    basic_query = f"""
    SELECT Id, Name, StageName, Amount, CloseDate, 
           (SELECT Id, ContentDocument.Title, ContentDocument.FileType 
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
    
    # Debug specific opportunity first
    debug_specific_opportunity(sf, "Binderholz")
    
    # Get closed opportunities
    get_closed_opportunities(sf, limit=20)
    
    # Optional: Query for a specific closed opportunity by name
    print("\n\n🔍 Would you like to search for a specific opportunity? (y/n): ", end="")
    if input().lower() == 'y':
        print("Enter opportunity name (or part of it): ", end="")
        search_term = input()
        
        query = f"""
        SELECT Id, Name, AccountId, Account.Name, StageName, Amount, CloseDate, 
               Type, LeadSource, Description,
               (SELECT Id, ContentDocument.Title, ContentDocument.FileType, 
                       ContentDocument.ContentSize, ContentDocument.CreatedDate
                FROM ContentDocumentLinks
                LIMIT 3)
        FROM Opportunity 
        WHERE StageName = 'Closed Won' AND Name LIKE '%{search_term}%'
        LIMIT 50
        """
        
        try:
            result = sf.query(query)
            # Filter search results to only include opportunities with files
            search_results = []
            for opp in result['records']:
                content_links = opp.get('ContentDocumentLinks')
                if content_links and content_links.get('records'):
                    search_results.append(opp)
            
            if search_results:
                print(f"\n✅ Found {len(search_results)} matching opportunities with files:")
                for opp in search_results:
                    print(f"\n   - {opp['Name']}")
                    print(f"     Account: {opp['Account']['Name'] if opp['Account'] else 'N/A'}")
                    print(f"     Amount: ${opp['Amount']:,.2f}" if opp['Amount'] else "     Amount: N/A")
                    print(f"     Close Date: {opp['CloseDate']}")
                    print(f"     Stage: {opp['StageName']}")
                    
                    # Display attached files for search results
                    content_links = opp.get('ContentDocumentLinks')
                    files = content_links.get('records', []) if content_links else []
                    if files:
                        print(f"     📎 Files: {', '.join([f['ContentDocument']['Title'] for f in files])}")
                    else:
                        print(f"     📎 No files attached")
            else:
                print(f"No closed won opportunities with files found matching '{search_term}'")
        except Exception as e:
            print(f"❌ Error searching: {e}")

if __name__ == "__main__":
    main()