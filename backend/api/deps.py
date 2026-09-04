"""
FastAPI dependency injection singletons.
All module-level state initialized once at app startup via lifespan in main.py.
"""
from backend.config import settings
from backend.audit.log import InMemoryAuditLogger
from backend.db.seed_catalog import InMemoryCatalogRepository
from backend.mandates.chain import MandateChain
from backend.payments.razorpay_client import RazorpayClient

# Singletons — safe to build at import time (no LLM, no network)
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

# BuyerAgentNode singleton — initialized lazily on first request so that
# OPENAI_API_KEY is guaranteed to be in os.environ (set by lifespan in main.py)
_buyer_agent = None


def get_buyer_agent():
    """
    Return the singleton BuyerAgentNode.
    MUST be called after the lifespan startup has set OPENAI_API_KEY in os.environ.
    """
    global _buyer_agent
    if _buyer_agent is None:
        from backend.agent.node import BuyerAgentNode
        _buyer_agent = BuyerAgentNode(model_name="gpt-4o-mini", temperature=0.3)
    return _buyer_agent
