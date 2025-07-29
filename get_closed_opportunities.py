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
    Query Salesforce for closed won opportunities and display their details
    """
    print(f"\n📊 Querying for closed won opportunities (limit: {limit})...")
    
    # SOQL query for closed won opportunities
    query = f"""
    SELECT Id, Name, AccountId, Account.Name, StageName, Amount, CloseDate, 
           Type, LeadSource, Description, CreatedDate, LastModifiedDate,
           Owner.Name, Owner.Email
    FROM Opportunity 
    WHERE StageName = 'Closed Won' 
    ORDER BY CloseDate DESC 
    LIMIT {limit}
    """
    
    try:
        result = sf.query(query)
        opportunities = result['records']
        
        if not opportunities:
            print("No closed won opportunities found.")
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
            
            print("-" * 100)
        
        # Summary statistics
        total_amount = sum(opp['Amount'] or 0 for opp in opportunities)
        print(f"\n📈 Summary:")
        print(f"   Total Opportunities: {len(opportunities)}")
        print(f"   Total Amount: ${total_amount:,.2f}")
        
        # Get won vs lost breakdown
        won_opps = [opp for opp in opportunities if 'won' in opp['StageName'].lower()]
        lost_opps = [opp for opp in opportunities if 'lost' in opp['StageName'].lower()]
        
        print(f"   Won: {len(won_opps)}")
        print(f"   Lost: {len(lost_opps)}")
        print(f"   Other: {len(opportunities) - len(won_opps) - len(lost_opps)}")
        
    except Exception as e:
        print(f"❌ Error querying opportunities: {e}")
        return

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
    get_closed_opportunities(sf, limit=20)
    
    # Optional: Query for a specific closed opportunity by name
    print("\n\n🔍 Would you like to search for a specific opportunity? (y/n): ", end="")
    if input().lower() == 'y':
        print("Enter opportunity name (or part of it): ", end="")
        search_term = input()
        
        query = f"""
        SELECT Id, Name, AccountId, Account.Name, StageName, Amount, CloseDate, 
               Type, LeadSource, Description
        FROM Opportunity 
        WHERE StageName = 'Closed Won' AND Name LIKE '%{search_term}%'
        LIMIT 5
        """
        
        try:
            result = sf.query(query)
            if result['records']:
                print(f"\n✅ Found {len(result['records'])} matching opportunities:")
                for opp in result['records']:
                    print(f"\n   - {opp['Name']}")
                    print(f"     Account: {opp['Account']['Name'] if opp['Account'] else 'N/A'}")
                    print(f"     Amount: ${opp['Amount']:,.2f}" if opp['Amount'] else "     Amount: N/A")
                    print(f"     Close Date: {opp['CloseDate']}")
                    print(f"     Stage: {opp['StageName']}")
            else:
                print(f"No closed won opportunities found matching '{search_term}'")
        except Exception as e:
            print(f"❌ Error searching: {e}")

if __name__ == "__main__":
    main()