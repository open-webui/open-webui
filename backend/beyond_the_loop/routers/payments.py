import stripe
from datetime import datetime
from pydantic import BaseModel
from fastapi import Depends, HTTPException, Request, Header, APIRouter
import os
from typing import Optional
import time

from beyond_the_loop.models.users import Users
from beyond_the_loop.models.companies import Companies
from beyond_the_loop.models.stripe_payment_histories import StripePaymentHistories

from open_webui.utils.auth import get_verified_user

router = APIRouter()

webhook_secret = os.environ.get('WEBHOOK_SECRET')
stripe.api_key = os.environ.get('STRIPE_API_KEY')

# Constants
FLEX_CREDITS_DEFAULT_PRICE_IN_CENTS = 2000 # Amount in cents (20 euro)

# Subscription Plans
SUBSCRIPTION_PLANS = {
    "free": {
        "name": "Free",
        "price_monthly": 0,
        "credits_per_month": 5,
        "stripe_price_id": "price_1RSIfGBBwyxb4MZjoc5Oz8zJ",
        "seats": 1
    },
    "starter": {
        "name": "Starter",
        "price_monthly": 2500,  # 25€ in cents
        "credits_per_month": 5,
        "stripe_price_id": "price_1RNqhyBBwyxb4MZjNJU4b13w",
        "seats": 5
    },
    "team": {
        "name": "Business",
        "price_monthly": 14900,  # 149€ in cents
        "credits_per_month": 50,
        "stripe_price_id": "price_1RNqiZBBwyxb4MZj6bXjHenV",
        "seats": 25
    },
    "growth": {
        "name": "Growth",
        "price_monthly": 84900,  # 849€ in cents
        "credits_per_month": 150,
        "stripe_price_id": "price_1RNqj4BBwyxb4MZjz4vVypid",
        "seats": 1000
    }
}

class SubscriptionPlanResponse(BaseModel):
    """Response model for subscription plans"""
    id: str
    name: str
    price_monthly: int
    credits_per_month: int
    seats: int

class SubscriptionResponse(BaseModel):
    """Response model for company subscription details"""
    plan: str
    status: str
    start_date: Optional[int] = None
    end_date: Optional[int] = None
    credits_remaining: Optional[int] = None

class CreateSubscriptionRequest(BaseModel):
    """Request model for creating a subscription"""
    plan_id: str  # "basic", "pro", or "team"

class UpdateSubscriptionRequest(BaseModel):
    """Request model for updating a subscription"""
    plan_id: str  # "basic", "pro", or "team"


# Creates a subscription checkout session in Stripe and returns the URL
@router.post("/create-subscription-session/")
async def create_subscription_session(request: CreateSubscriptionRequest, user=Depends(get_verified_user)):
    try:
        if request.plan_id == "free" or request.plan_id not in SUBSCRIPTION_PLANS:
            raise HTTPException(status_code=400, detail=f"Invalid plan ID: {request.plan_id}")

        plan = SUBSCRIPTION_PLANS[request.plan_id]
        stripe_price_id = plan["stripe_price_id"]
        
        if not stripe_price_id:
            raise HTTPException(status_code=400, detail=f"Stripe price ID not configured for plan: {request.plan_id}")
            
        company = Companies.get_company_by_id(user.company_id)
        stripe_customer_id = company.stripe_customer_id

        if not stripe_customer_id:
            raise HTTPException(status_code=400, detail="No Stripe customer found for this company")

        # Create a new Stripe Checkout session for the new subscription
        print(f"Creating new subscription with price ID: {stripe_price_id} for plan: {request.plan_id}")
        
        # Check for existing subscriptions to include in metadata
        existing_subscriptions = stripe.Subscription.list(
            customer=stripe_customer_id,
            status='all',
            limit=10
        )
        
        # Collect IDs of existing subscriptions to cancel after payment
        subscription_ids_to_cancel = [sub.id for sub in existing_subscriptions.data if sub.status in ['active', 'trialing']]
        
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': stripe_price_id,
                'quantity': 1,
            }],
            mode='subscription',
            customer=stripe_customer_id,
            success_url=os.getenv('BACKEND_ADDRESS') + "?modal=company-settings&tab=billing",
            cancel_url=os.getenv('BACKEND_ADDRESS'),
            subscription_data={
                'metadata': {
                    'company_id': user.company_id,
                    'plan_id': request.plan_id,
                    'user_email': user.email,
                    'subscriptions_to_cancel': ','.join(subscription_ids_to_cancel) if subscription_ids_to_cancel else ''
                }
            }
        )
        return {"url": session.url}
    except Exception as e:
        print(f"Error creating subscription session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Get all available subscription plans
@router.get("/subscription-plans/")
async def get_subscription_plans():
    """Get all available subscription plans"""
    plans = []
    for plan_id, plan_details in SUBSCRIPTION_PLANS.items():
        plans.append(SubscriptionPlanResponse(
            id=plan_id,
            name=plan_details["name"],
            price_monthly=plan_details["price_monthly"],
            credits_per_month=plan_details["credits_per_month"],
            seats=plan_details["seats"]
        ))
    return plans


# Get current subscription details
@router.get("/subscription/")
async def get_subscription(user=Depends(get_verified_user)):
    """Get the current subscription details for the company"""
    try:
        company = Companies.get_company_by_id(user.company_id)

        if company.stripe_customer_id is None:
            return {
                "plan": "free",
                "flex_credits_remaining": company.flex_credit_balance,
                "credits_remaining": company.credit_balance,
                "seats": 1,
                "seats_taken": Users.count_users_by_company_id(user.company_id),
                "auto_recharge": company.auto_recharge
            }

        # Get subscription from Stripe
        subscriptions = stripe.Subscription.list(
            customer=company.stripe_customer_id,
            status='active',
            limit=1
        )

        # Check for trial subscriptions
        trial_subscriptions = stripe.Subscription.list(
            customer=company.stripe_customer_id,
            status='trialing',
            limit=1
        )

        # If there's an active trial subscription
        if trial_subscriptions.data and len(trial_subscriptions.data) > 0 and not subscriptions.data:
            trial_subscription = trial_subscriptions.data[0]
            
            # Calculate days remaining in trial
            current_time = int(time.time())
            trial_end = trial_subscription.trial_end
            days_remaining = max(0, int((trial_end - current_time) / (24 * 60 * 60)))
            
            return {
                'credits_remaining': company.credit_balance,
                'flex_credits_remaining': company.flex_credit_balance,
                'plan': 'free',
                'is_trial': True,
                "seats": 1,
                "seats_taken": Users.count_users_by_company_id(user.company_id),
                'trial_end': trial_end,
                'days_remaining': days_remaining
            }

        if not subscriptions.data:
            return {
                'credits_remaining': company.credit_balance,
                'plan': 'free'
            }

        subscription = subscriptions.data[0]

        plan_id = subscription.metadata.get('plan_id', 'free')

        plan = SUBSCRIPTION_PLANS[plan_id] or {}

        return {
            "plan": plan_id,
            "status": subscription.status,
            "start_date": subscription.current_period_start,
            "end_date": subscription.current_period_end,
            "cancel_at_period_end": subscription.cancel_at_period_end,
            "canceled_at": subscription.canceled_at if hasattr(subscription, 'canceled_at') else None,
            "will_renew": not subscription.cancel_at_period_end and subscription.status == 'active',
            "next_billing_date": subscription.current_period_end if not subscription.cancel_at_period_end and subscription.status == 'active' else None,
            "flex_credits_remaining": company.flex_credit_balance,
            "credits_remaining": company.credit_balance,
            "seats": plan.get("seats", 0),
            "seats_taken": Users.count_users_by_company_id(user.company_id),
            "auto_recharge": company.auto_recharge
        }
    except Exception as e:
        print(f"Error getting subscription: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Cancel subscription
@router.delete("/subscription/")
async def cancel_subscription(user=Depends(get_verified_user)):
    """Cancel the current subscription"""
    try:
        company = Companies.get_company_by_id(user.company_id)
        if not company.stripe_customer_id:
            raise HTTPException(status_code=404, detail="No active subscription found")
            
        # Get subscription from Stripe
        subscriptions = stripe.Subscription.list(
            customer=company.stripe_customer_id,
            status='active',
            limit=1
        )
        
        if not subscriptions.data:
            raise HTTPException(status_code=404, detail="No active subscription found")
            
        subscription = subscriptions.data[0]
        
        # Cancel subscription at period end
        stripe.Subscription.modify(
            subscription.id,
            cancel_at_period_end=True
        )
        
        return {"message": "Subscription will be canceled at the end of the billing period"}
    except Exception as e:
        print(f"Error canceling subscription: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Called by stripe after payment process is done
@router.post("/checkout-webhook")
async def checkout_webhook(request: Request, stripe_signature: str = Header(None)):
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="No Stripe signature provided")

    payload = await request.body()
    try:
        # Verify Stripe Webhook Signature
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=stripe_signature,
            secret=webhook_secret
        )

        event_type = event.get("type")
        event_data = event.get("data", {}).get("object", {})

        # Payment via Stripe checkout
        if event_type == "checkout.session.completed":
            if event_data.get("payment_status") == "paid":
                handle_checkout_session_completed(event_data)
                return

        # Subscription events
        elif event_type == "customer.subscription.created":
            handle_subscription_created(event_data)
            return
            
        elif event_type == "customer.subscription.updated":
            handle_subscription_updated(event_data)
            return
            
        elif event_type == "customer.subscription.deleted":
            handle_subscription_deleted(event_data)
            return
            
        elif event_type == "invoice.payment_succeeded":
            handle_invoice_payment_succeeded(event_data)
            return

        # Automatic recharging - skipped it from checkout session
        elif event_type == "payment_intent.succeeded":
            handle_payment_intent_succeeded(event_data)
            return

        elif event_type == "payment_intent.payment_failed":
            handle_payment_failed(event_data)
            return

        else:
            print(f"Unhandled Stripe event type: {event_type}")

        return {"message": "Webhook processed successfully"}

    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")
    except Exception as e:
        print(f"Webhook processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def handle_payment_failed(event_data):
    try:
        payment_intent_id = event_data.get("id")
        charges = event_data.get("charges", {}).get("data", [])
        failure_reason = event_data.get("last_payment_error", {}).get("message", "Unknown reason")

        customer_email = event_data.get("metadata", {}).get("customer_email")

        if not customer_email:
            print(f"Failed payment: Customer email not found for PaymentIntent {payment_intent_id}.")
            return

        user = Users.get_user_by_email(customer_email)
        company = Companies.get_company_by_id(user.company_id) if user else None

        payment_data = {
            "id": f"payment_{payment_intent_id}",
            "stripe_transaction_id": payment_intent_id,
            "company_id": company.id if company else None,
            "user_id": user.id if user else None,
            "description": "Payment Failed",
            "charged_amount": event_data.get("amount", 0) / 100,
            "currency": event_data.get("currency", "unknown"),
            "payment_status": "failed",
            "payment_method": "card",
            "payment_date": datetime.utcfromtimestamp(event_data.get("created", datetime.utcnow().timestamp())),
            "payment_metadata": event_data.get("metadata", {}),
            "failure_reason": failure_reason,
        }

        StripePaymentHistories.log_payment(payment_data)

        print(f"Logged failed payment for {customer_email} with reason: {failure_reason}")

    except Exception as e:
        print(f"Error handling payment_intent.payment_failed: {e}")


def handle_checkout_session_completed(data):
    """
    Handle the checkout.session.completed event from Stripe.
    For subscriptions, we only need to ensure the customer ID is saved.
    The actual subscription processing happens in customer.subscription.created event.
    """
    try:
        user_email = data["customer_details"]["email"]
        user = Users.get_user_by_email(user_email)
        
        if not user:
            print(f"User not found with email: {user_email}")
            return
            
        company = Companies.get_company_by_id(user.company_id)
        if not company:
            print(f"Company not found for user: {user_email}")
            return
            
        # Save Stripe Customer ID if missing
        if not company.stripe_customer_id:
            Companies.update_company_by_id(user.company_id, {"stripe_customer_id": data["customer"]})
            print(f"Updated Stripe customer ID for company {user.company_id}")
            
        print(f"Checkout session completed for user {user_email}")
        
    except Exception as e:
        print(f"Error handling checkout.session.completed: {e}")


def handle_subscription_created(event_data):
    """
    Handle the customer.subscription.created event from Stripe.
    This is triggered when a new subscription is created.
    """
    try:
        # event_data is already the subscription object from the webhook handler
        subscription = event_data
        status = subscription['status']
        metadata = subscription['metadata']
        
        # Get the plan ID from metadata
        plan_id = metadata.get('plan_id')
        company_id = metadata.get('company_id')
        
        if not plan_id or not company_id:
            print("Missing plan_id or company_id in subscription metadata")
            return
            
        # Check if there are subscriptions to cancel
        subscriptions_to_cancel = metadata.get('subscriptions_to_cancel', '')

        print(subscriptions_to_cancel)

        if subscriptions_to_cancel:
            subscription_ids = subscriptions_to_cancel.split(',')
            for sub_id in subscription_ids:
                if sub_id and sub_id != subscription['id']:  # Don't cancel the new subscription
                    try:
                        stripe.Subscription.delete(sub_id)
                        print(f"Cancelled old subscription {sub_id} after new subscription {subscription['id']} was created")
                    except Exception as e:
                        print(f"Error cancelling subscription {sub_id}: {e}")
        
        # Get the company from the database
        company = Companies.get_company_by_id(company_id)
        if not company:
            print(f"Company {company_id} not found")
            return
        
        # For trial subscriptions, set initial credit balance to 5
        if status == "trialing":
            Companies.update_company_by_id(company_id, {
                "credit_balance": SUBSCRIPTION_PLANS[plan_id]["credits_per_month"],  # credits for trial as specified
            })
            print(f"Trial subscription created for company {company_id} with 5 initial credits")
            return
            
        # For regular subscriptions, handle as before
        if plan_id not in SUBSCRIPTION_PLANS:
            print(f"Invalid plan ID: {plan_id} for subscription {subscription['id']}")
            return
            
        plan = SUBSCRIPTION_PLANS[plan_id]
        
        # Update company credit balance
        Companies.update_company_by_id(company_id, {
            "credit_balance": plan["credits_per_month"]
        })
        
        print(f"Subscription created for company {company_id} with plan {plan_id}")
        
    except Exception as e:
        print(f"Error handling subscription.created: {e}")


def handle_subscription_updated(event_data):
    try:
        # event_data is already the subscription object
        subscription_id = event_data.get("id")
        customer_id = event_data.get("customer")
        metadata = event_data.get("metadata", {})
        
        # Get company by customer ID
        company = Companies.get_company_by_stripe_customer_id(customer_id)
        if not company:
            print(f"Company not found for customer ID: {customer_id}")
            return
            
        # Check if plan was changed
        plan_id = metadata.get("plan_id")
        if plan_id and plan_id in SUBSCRIPTION_PLANS:
            # Plan was changed, update credits on next renewal
            print(f"Subscription updated for company {company.id} with new plan {plan_id}")
        
    except Exception as e:
        print(f"Error handling subscription.updated: {e}")


def handle_subscription_deleted(event_data):
    try:
        # event_data is already the subscription object
        subscription_id = event_data.get("id")
        customer_id = event_data.get("customer")
        
        # Get company by customer ID
        company = Companies.get_company_by_stripe_customer_id(customer_id)
        if not company:
            print(f"Company not found for customer ID: {customer_id}")
            return
            
        # No need to update anything in our database since we query Stripe directly
        print(f"Subscription deleted for company {company.id}")
        
    except Exception as e:
        print(f"Error handling subscription.deleted: {e}")


def handle_invoice_payment_succeeded(event_data):
    try:
        # event_data is already the invoice object
        invoice_id = event_data.get("id")
        customer_id = event_data.get("customer")
        subscription_id = event_data.get("subscription")
        
        if not subscription_id:
            # Not a subscription invoice
            return
            
        # Get company by customer ID
        company = Companies.get_company_by_stripe_customer_id(customer_id)
        if not company:
            print(f"Company not found for customer ID: {customer_id}")
            return
            
        # Get subscription details
        subscription = stripe.Subscription.retrieve(subscription_id)
        plan_id = subscription.metadata.get("plan_id")
        
        if not plan_id or plan_id not in SUBSCRIPTION_PLANS:
            print(f"Invalid plan ID: {plan_id} for subscription {subscription_id}")
            return
            
        plan = SUBSCRIPTION_PLANS[plan_id]
        
        # Reset credit balance for the new billing period
        Companies.update_company_by_id(company.id, {
            "credit_balance": plan["credits_per_month"],
            "budget_mail_80_sent": False,
            "budget_mail_100_sent": False
        })

        print(f"Credits renewed for company {company.id} with plan {plan_id}")
        
    except Exception as e:
        print(f"Error handling invoice.payment_succeeded: {e}")


def handle_payment_intent_succeeded(data):
    try:
        # event_data is already the payment intent object
        payment_intent_id = data.get("id")
        customer_id = data.get("customer")
        
        if not customer_id:
            print(f"Customer ID not found for PaymentIntent {payment_intent_id}")
            return
        
        company = Companies.get_company_by_stripe_customer_id(customer_id)

        if not company:
            print(f"Company not found for customer ID: {customer_id}")
            return
        
        # Check if this is from a checkout session
        if data.get("metadata", {}).get("from_checkout_session") == "true":
            # Already handled by checkout.session.completed
            return
            
        # Check if this payment was already logged (from manual recharge)
        if data.get("metadata", {}).get("flex_credits_recharge") == "true":
            Companies.add_flex_credit_balance(company.id, FLEX_CREDITS_DEFAULT_PRICE_IN_CENTS / 100)

            Companies.update_company_by_id(company.id, {"budget_mail_80_sent": False, "budget_mail_100_sent": False})

            payment_data = {
                "id": f"payment_{payment_intent_id}",
                "stripe_transaction_id": payment_intent_id,
                "company_id": company.id,
                "description": "Flex Credits Recharge",
                "charged_amount": FLEX_CREDITS_DEFAULT_PRICE_IN_CENTS / 100,
                "currency": data.get("currency", "eur"),
                "payment_status": "succeeded",
                "payment_method": "card",
                "payment_date": datetime.utcfromtimestamp(data.get("created")),
                "payment_metadata": data.get("metadata", {}),
            }
        else:
            payment_data = {
                "id": f"payment_{payment_intent_id}",
                "stripe_transaction_id": payment_intent_id,
                "company_id": company.id,
                "description": "Monthly Auto-Recharge",
                "charged_amount": data.get("amount", 0) / 100,
                "currency": data.get("currency", "eur"),
                "payment_status": "succeeded",
                "payment_method": "card",
                "payment_date": datetime.utcfromtimestamp(data.get("created")),
                "payment_metadata": data.get("metadata", {}),
            }

        StripePaymentHistories.log_payment(payment_data)
        
        print(f"Auto-recharge successful for company {company.id}")
        
    except Exception as e:
        print(f"Error handling payment_intent.succeeded: {e}")


@router.get("/customer-billing-page/")
async def customer_billing_page(user=Depends(get_verified_user)):
    try:
        company = Companies.get_company_by_id(user.company_id)
        
        if not company.stripe_customer_id:
            raise HTTPException(status_code=400, detail="No stripe customer method found for company")
        
        # Create a billing portal session
        session = stripe.billing_portal.Session.create(
            customer=company.stripe_customer_id,
            return_url=os.getenv('BACKEND_ADDRESS')
        )
        
        return {"url": session.url}
    except Exception as e:
        print(f"Error creating billing portal: {e}")
        raise HTTPException(status_code=500, detail="Failed to create billing portal")


class UpdateAutoRechargeRequest(BaseModel):
    auto_recharge: bool

@router.post("/update-auto-recharge/")
async def update_auto_recharge(request: UpdateAutoRechargeRequest, user=Depends(get_verified_user)):
    try:
        result = Companies.update_auto_recharge(user.company_id, request.auto_recharge)
        if result:
            return {"message": f"Auto-recharge {'enabled' if request.auto_recharge else 'disabled'} successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to update auto-recharge setting")
    except Exception as e:
        print(f"Error updating auto-recharge: {e}")
        raise HTTPException(status_code=500, detail="Failed to update auto-recharge setting")

@router.post("/recharge-flex-credits/")
async def recharge_flex_credits(user=Depends(get_verified_user)):
    try:
        company = Companies.get_company_by_id(user.company_id)
        
        if not company.stripe_customer_id:
            raise HTTPException(status_code=400, detail="No active subscription found. Please subscribe first.")
        
        # Get the customer's payment methods
        payment_methods = stripe.PaymentMethod.list(
            customer=company.stripe_customer_id,
            type="card"
        )
        
        # Check if the customer has any payment methods
        if not payment_methods or len(payment_methods.data) == 0:
            raise HTTPException(
                status_code=400, 
                detail="No payment method found. Please add a payment method in your billing settings."
            )
            
        # Use the first payment method
        default_payment_method = payment_methods.data[0].id
        
        # Create a PaymentIntent
        payment_intent = stripe.PaymentIntent.create(
            amount=FLEX_CREDITS_DEFAULT_PRICE_IN_CENTS,
            currency="eur",
            customer=company.stripe_customer_id,
            payment_method=default_payment_method,  # Specify the payment method
            payment_method_types=["card"],
            off_session=True,
            confirm=True,
            metadata={
                "company_id": company.id,
                "user_id": user.id,
                "user_email": user.email,
                "recharge_type": "manual",
                "flex_credits_recharge": "true"
            }
        )

        return {"message": "Credits recharged successfully", "payment_intent": payment_intent.id}
        
    except stripe.error.CardError as e:
        # Card declined
        raise HTTPException(status_code=400, detail=f"Card declined: {e.error.message}")
    except Exception as e:
        print(f"Error recharging credits: {e}")
        raise HTTPException(status_code=500, detail="Failed to recharge credits")
