from dotenv import load_dotenv
from pydantic import BaseModel, Field
import os


load_dotenv()


class Settings(BaseModel):
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
    quote_signing_secret: str = Field(
        default="change_me_dev_secret", validation_alias="QUOTE_SIGNING_SECRET"
    )


settings = Settings.model_validate(os.environ)
