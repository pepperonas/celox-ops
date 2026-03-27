from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://celox:celox@localhost:5432/celox_ops"
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24

    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD_HASH: str = ""

    BUSINESS_NAME: str = ""
    BUSINESS_OWNER: str = ""
    BUSINESS_ADDRESS: str = ""
    BUSINESS_EMAIL: str = ""
    BUSINESS_WEB: str = ""
    BUSINESS_TAX_ID: str = ""
    BUSINESS_TAX_NUMBER: str = ""
    BUSINESS_BANK_NAME: str = ""
    BUSINESS_BANK_IBAN: str = ""
    BUSINESS_BANK_BIC: str = ""
    KLEINUNTERNEHMER: bool = True

    PDF_STORAGE_PATH: str = "/data/invoices"
    LOGO_PATH: str = "/data/assets/logo.png"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
