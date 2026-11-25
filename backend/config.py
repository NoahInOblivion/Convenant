from decimal import Decimal
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://covenant:covenant@localhost:5432/covenant"
    openai_api_key: str = ""
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    mandate_secret_key: str = "a" * 64
    spend_cap: Decimal = Decimal("10000.00")
    mandate_intent_ttl_seconds: int = 900
    mandate_cart_ttl_seconds: int = 600
    mandate_payment_ttl_seconds: int = 300
    human_approval_timeout_seconds: int = 300

settings = Settings()
