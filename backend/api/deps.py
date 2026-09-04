"""
FastAPI dependency injection singletons.
All module-level state initialized once at app startup.
"""
from decimal import Decimal
from backend.config import settings
from backend.audit.log import InMemoryAuditLogger
from backend.db.seed_catalog import InMemoryCatalogRepository
from backend.mandates.chain import MandateChain
from backend.payments.razorpay_client import RazorpayClient
from backend.replan.loop import ReplanLoop

# Singletons
audit_logger = InMemoryAuditLogger()
catalog = InMemoryCatalogRepository()
seen_idempotency_keys: set[str] = set()

mandate_chain = MandateChain(
    secret_key=settings.mandate_secret_key,
    intent_ttl=settings.mandate_intent_ttl_seconds,
    cart_ttl=settings.mandate_cart_ttl_seconds,
    payment_ttl=settings.mandate_payment_ttl_seconds,
)

razorpay_client = RazorpayClient(
    key_id=settings.razorpay_key_id,
    key_secret=settings.razorpay_key_secret,
    secret_key=settings.mandate_secret_key,
)


def get_buyer_agent():
    """Lazy-initialize BuyerAgentNode (requires OPENAI_API_KEY)."""
    from backend.agent.node import BuyerAgentNode
    return BuyerAgentNode(model_name="gpt-4o-mini", temperature=0.3)
