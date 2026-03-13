import json
from decimal import Decimal

from pydantic import BaseModel, Field

from support_swarm.db.engine import get_session
from support_swarm.db.models import EmailLog, Order, Refund
from support_swarm.tools.registry import register_tool


class LookupOrderInput(BaseModel):
    """Input for looking up orders."""

    order_id: str = Field(
        default="",
        description="The order identifier in ORD-XXXX format (e.g. 'ORD-1001')",
    )
    customer_email: str = Field(
        default="", description="Customer email address to look up all their orders"
    )


class ProcessRefundInput(BaseModel):
    """Input for processing a refund."""

    order_id: str = Field(
        description="The order to refund in ORD-XXXX format (e.g. 'ORD-1001')"
    )
    amount: float = Field(description="Dollar amount to refund, must be positive")


class SendEmailInput(BaseModel):
    """Input for sending an email."""

    customer_email: str = Field(description="Recipient email address")
    subject: str = Field(description="Email subject line")
    body: str = Field(description="Full email body text")


@register_tool(args_schema=LookupOrderInput)
def lookup_order(order_id: str = "", customer_email: str = "") -> str:
    """Look up orders by order ID or customer email."""
    if not order_id and not customer_email:
        return json.dumps({"error": "Provide order_id or customer_email."})

    with get_session() as session:
        if order_id:
            order = Order.get_by_id(session, order_id)
            if not order:
                return json.dumps({"error": "No orders found."})
            return json.dumps(_serialize_order(order), indent=2)
        orders = Order.get_by_customer_email(session, customer_email)
        if not orders:
            return json.dumps({"error": "No orders found."})
        return json.dumps([_serialize_order(o) for o in orders], indent=2)


def _serialize_order(order) -> dict:
    return {
        "order_id": order.id,
        "status": order.status,
        # BUG #1: items stripped to names only (prices removed) — LLM can't see costs
        # FIX #1: uncomment the next line, comment/delete the line after it
        # "items": order.items,
        "items": [{"name": i["name"], "qty": i["qty"]} for i in order.items],
        "shipping_address": order.shipping_address,
        "delivery_date": order.delivery_date,
        # BUG #1: total_amount hidden — LLM can't verify refund amount against order total
        # FIX #1: uncomment the next line
        # "total_amount": float(order.total_amount),
        "notes": order.notes,
        "customer_name": order.customer.name,
        "customer_email": order.customer.email,
        "created_at": order.created_at.isoformat(),
    }


@register_tool(args_schema=ProcessRefundInput)
def process_refund(order_id: str, amount: float) -> str:
    """Initiate a refund for an order."""
    # BUG #2: All validation removed — accepts any order_id and any amount
    # FIX #2: uncomment the validation block below
    # if amount <= 0:
    #     return json.dumps(
    #         {"success": False, "error": "Refund amount must be positive."}
    #     )

    with get_session() as session:
        # FIX #2 (continued): uncomment the order check below
        # order = Order.get_by_id(session, order_id)
        # if not order:
        #     return json.dumps(
        #         {"success": False, "error": f"Order {order_id} not found."}
        #     )
        # if amount > float(order.total_amount):
        #     return json.dumps(
        #         {
        #             "success": False,
        #             "error": f"Refund ${amount:.2f} exceeds order total ${float(order.total_amount):.2f}.",
        #         }
        #     )

        refund = Refund.create(
            session,
            order_id=order_id,
            amount=Decimal(str(amount)),
            reason="Customer-initiated refund via ShopAssist",
            status="processed",
        )
        return json.dumps(
            {
                "success": True,
                "refund_id": str(refund.id),
                "order_id": order_id,
                "amount": float(refund.amount),
                "status": refund.status,
            },
            indent=2,
        )


@register_tool(args_schema=SendEmailInput)
def send_email(customer_email: str, subject: str, body: str) -> str:
    """Send an email to the customer."""
    with get_session() as session:
        email = EmailLog.create(
            session, customer_email=customer_email, subject=subject, body=body
        )
        return json.dumps(
            {
                "email_id": str(email.id),
                "customer_email": email.customer_email,
                "subject": email.subject,
                "sent_at": email.sent_at.isoformat(),
            },
            indent=2,
        )
