from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    app_name: str = "Closed Opportunities Script"
    app_version: str = "1.0.0"
    
    # Salesforce Configuration - OAuth2 Connected App Method (Recommended)
    salesforce_consumer_key: Optional[str] = None
    salesforce_consumer_secret: Optional[str] = None
    salesforce_instance_url: Optional[str] = None
    salesforce_access_token: Optional[str] = None
    
    # Salesforce Configuration - Username/Password Method (Alternative)
    salesforce_username: Optional[str] = None
    salesforce_password: Optional[str] = None
    salesforce_security_token: Optional[str] = None
    
    # Salesforce Domain Configuration
    salesforce_domain: str = "test"  # "login" for production, "test" for sandbox
    salesforce_custom_domain: Optional[str] = None  # e.g. "vector-solutions--dev1.sandbox.lightning.force.com"
    
    class Config:
        env_file = ".env"


settings = Settings()