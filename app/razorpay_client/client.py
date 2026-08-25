from typing import TYPE_CHECKING

from app.config import settings

if TYPE_CHECKING:
    import razorpay


def get_client() -> "razorpay.Client":
    import razorpay

    return razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))
