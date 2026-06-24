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

    # ── Catálogo público (Sprint 3) ──────────────────────────────────────────
    # Número del negocio para el botón "Consultar por WhatsApp" del catálogo.
    # Formato internacional sin +: "591XXXXXXXXX" (Bolivia).
    whatsapp_catalog_phone: str = "591XXXXXXXXX"

    # Template del mensaje pre-llenado. Soporta {product_name} y {sku}.
    whatsapp_message_template: str = (
        "Hola, me interesa el producto *{product_name}* (SKU: {sku}). "
        "¿Podría darme más información?"
    )

    # Si True, muestra base_price en el catálogo público.
    catalog_show_prices: bool = True

    # Símbolo de moneda mostrado en el catálogo.
    catalog_currency_symbol: str = "Bs."

    # URL base para construir URLs de imágenes subidas localmente.
    media_base_url: str = "http://localhost:8000"

    # Path local donde el backend guarda las imágenes subidas.
    media_local_path: str = "./media"

    # ── Catálogo revista (Sprint 4) ──────────────────────────────────────────
    # Texto de la marca de agua que se "quema" en las imágenes subidas (anti-plagio).
    watermark_text: str = "BLACK HORSE"
    # URL pública del sitio (frontend) que codifica el QR para compartir.
    catalog_public_base_url: str = "http://localhost:3000"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"


settings = Settings()
