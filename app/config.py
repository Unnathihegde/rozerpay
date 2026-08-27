from dotenv import load_dotenv
from pydantic import BaseModel, Field, model_validator
import os


load_dotenv()


class Settings(BaseModel):
    app_env: str = Field(default="local", validation_alias="APP_ENV")
    razorpay_key_id: str = Field(
        default="rzp_test_xxxxxxxxxxxx", validation_alias="RAZORPAY_KEY_ID"
    )
    razorpay_key_secret: str = Field(
        default="xxxxxxxxxxxxxxxxxxxx", validation_alias="RAZORPAY_KEY_SECRET"
    )
    razorpay_webhook_secret: str = Field(
        default="whsec_xxxxxxxxxxxxxxxxxxxx", validation_alias="RAZORPAY_WEBHOOK_SECRET"
    )
    spend_limit_paise: int = Field(default=1000000, validation_alias="SPEND_LIMIT_PAISE")
    database_url: str = Field(default="sqlite:///./gateway.db", validation_alias="DATABASE_URL")
    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        validation_alias="CORS_ORIGINS",
    )
    quote_signing_secret: str = Field(
        default="change_me_dev_secret", validation_alias="QUOTE_SIGNING_SECRET"
    )

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.app_env.lower() in {"production", "staging"}:
            placeholders = {
                "RAZORPAY_KEY_ID": self.razorpay_key_id,
                "RAZORPAY_KEY_SECRET": self.razorpay_key_secret,
                "RAZORPAY_WEBHOOK_SECRET": self.razorpay_webhook_secret,
                "QUOTE_SIGNING_SECRET": self.quote_signing_secret,
            }
            invalid = [name for name, value in placeholders.items() if "xxxx" in value.lower() or value == "change_me_dev_secret"]
            if invalid:
                raise ValueError(f"production secrets must be configured: {', '.join(invalid)}")
        return self


settings = Settings.model_validate(os.environ)
