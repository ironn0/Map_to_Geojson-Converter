"""
Billing routes (Stripe-ready scaffolding) and quota visibility.
"""

from typing import Dict, Optional

from billing_store import get_plan_summary, set_user_plan, user_from_auth
from config import BILLING_ENABLED, BILLING_WEBHOOK_SECRET
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/billing", tags=["billing"])


class CheckoutRequest(BaseModel):
    target_plan: str


class WebhookEvent(BaseModel):
    event: str
    user_id: str
    plan: Optional[str] = None


def _require_user(authorization: str) -> Dict:
    user = user_from_auth(authorization)
    if not user:
        raise HTTPException(401, "Token non valido o mancante")
    return user


@router.get("/me")
async def billing_me(authorization: str = Header(default="", alias="Authorization")) -> Dict:
    if not BILLING_ENABLED:
        raise HTTPException(503, "Billing non abilitato")
    user = _require_user(authorization)
    summary = get_plan_summary(user["id"])
    return {"success": True, "billing": summary}


@router.post("/checkout")
async def billing_checkout(
    req: CheckoutRequest,
    authorization: str = Header(default="", alias="Authorization"),
) -> Dict:
    if not BILLING_ENABLED:
        raise HTTPException(503, "Billing non abilitato")
    user = _require_user(authorization)
    if req.target_plan not in {"pro", "team"}:
        raise HTTPException(400, "target_plan deve essere 'pro' o 'team'")
    fake_checkout_url = (
        f"https://checkout.stripe.com/pay/mock-session?"
        f"user={user['id']}&plan={req.target_plan}"
    )
    return {
        "success": True,
        "checkout_url": fake_checkout_url,
        "mode": "scaffold",
        "message": "Checkout Stripe mock generato. Integrare SDK Stripe in produzione.",
    }


@router.post("/webhook")
async def billing_webhook(
    payload: WebhookEvent,
    x_webhook_secret: str = Header(default="", alias="X-Webhook-Secret"),
) -> Dict:
    if not BILLING_ENABLED:
        raise HTTPException(503, "Billing non abilitato")
    if BILLING_WEBHOOK_SECRET and x_webhook_secret != BILLING_WEBHOOK_SECRET:
        raise HTTPException(401, "Webhook secret non valida")
    if payload.event != "subscription.updated":
        return {"success": True, "ignored": True}
    if not payload.plan:
        raise HTTPException(400, "plan obbligatorio per subscription.updated")
    try:
        summary = set_user_plan(payload.user_id, payload.plan)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"success": True, "billing": summary}
