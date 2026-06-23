from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Aplicación
    app_name: str = "Talabartería CMS-CRM"
    app_version: str = "0.1.0"
    environment: str = "development"

    # Base de datos
    database_url: str

    # Seguridad
    secret_key: str = "changeme"

    # WhatsApp Business API
    whatsapp_api_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_verify_token: str = ""

    @property
    def is_development(self) -> bool:
        return self.environment == "development"


settings = Settings()
