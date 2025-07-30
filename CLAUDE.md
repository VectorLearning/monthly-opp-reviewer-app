# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python application that connects to Salesforce to retrieve and analyze closed opportunities with file attachments. The application uses OAuth2 authentication with automatic token refresh and focuses specifically on "Closed Won" opportunities that have files/documents attached.

## Dependencies & Environment

- **Python Environment**: Use the virtual environment in `venv/` directory
- **Package Manager**: pip with requirements listed in `requirements.txt`
- **Key Dependencies**: 
  - `simple-salesforce` for Salesforce API integration
  - `pydantic-settings` for configuration management
  - `requests` for HTTP calls
  - `python-dotenv` for environment variable loading

## Common Commands

```bash
# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate     # On Windows

# Install dependencies
pip install -r requirements.txt

# Run the main application
python get_closed_opportunities.py
```

## Configuration

The application uses environment variables loaded from a `.env` file. Two authentication methods are supported:

1. **OAuth2 Client Credentials (Recommended)**:
   - `SALESFORCE_CONSUMER_KEY`
   - `SALESFORCE_CONSUMER_SECRET`
   - `SALESFORCE_INSTANCE_URL`

2. **Username/Password Fallback**:
   - `SALESFORCE_USERNAME`
   - `SALESFORCE_PASSWORD`
   - `SALESFORCE_SECURITY_TOKEN`

Additional configuration:
- `SALESFORCE_DOMAIN`: "test" for sandbox, "login" for production
- `SALESFORCE_CUSTOM_DOMAIN`: For custom domain URLs

## Architecture

### Core Components

1. **`config.py`**: Pydantic-based settings management using environment variables
2. **`token_manager.py`**: Singleton class handling OAuth token lifecycle with automatic refresh
3. **`get_closed_opportunities.py`**: Main application script with Salesforce integration

### Authentication Flow

The application uses a sophisticated token management system:
- Primary: OAuth2 client credentials flow with automatic refresh
- Fallback: Username/password authentication
- Token expiry handling with 5-minute buffer for refresh
- In-memory token storage (singleton pattern)

### Data Retrieval Logic

The application specifically targets:
- Opportunities with `StageName = 'Closed Won'`
- Only opportunities that have `ContentDocumentLinks` (files attached)
- Retrieves both opportunity details and attached file metadata
- Supports both modern ContentDocumentLinks and legacy Attachments

### Key Features

- **File-focused filtering**: Only shows opportunities with attachments
- **Comprehensive opportunity data**: Includes financial, timeline, and ownership information
- **File metadata display**: Shows file names, types, sizes, and creation dates
- **Interactive search**: Allows searching for specific opportunities by name
- **Summary statistics**: Provides totals, counts, and breakdowns

## File Structure

- `config.py`: Configuration and settings management
- `token_manager.py`: OAuth token lifecycle management  
- `get_closed_opportunities.py`: Main application logic
- `requirements.txt`: Python dependencies
- `README_OPPORTUNITIES.md`: User documentation and setup instructions
- `.env`: Environment variables (not in repo)
- `venv/`: Python virtual environment

## Development Notes

- The token manager implements singleton pattern for shared token state
- Error handling includes graceful fallback between authentication methods
- Salesforce queries use SOQL with nested relationships for file attachments
- The application filters results client-side to ensure only opportunities with files are displayed
- Hardcoded debug search for "Binderholz" opportunity in main function (line 246)