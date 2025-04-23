import stripe
from datetime import datetime
from pydantic import BaseModel
from fastapi import Depends, HTTPException, Request, Header, APIRouter
import os
import json

from beyond_the_loop.models.users import Users
from beyond_the_loop.models.companies import Companies
from beyond_the_loop.models.stripe_payment_histories import StripePaymentHistories

from open_webui.utils.auth import get_verified_user

router = APIRouter()

webhook_secret = os.environ.get('WEBHOOK_SECRET')
stripe.api_key = os.environ.get('STRIPE_API_KEY')

# Constants
AMOUNT = 2500 # Amount in cents (e.g., 25 euro)
CREDITS_TO_ADD = 20000

def create_and_finalize_invoice(stripe_customer_id, payment_intent_id, description="Credits Purchase"):
    """
    Create and finalize an invoice for a Stripe customer.
    """
    try:
        # Create an invoice item
        stripe.InvoiceItem.create(
            customer=stripe_customer_id,
            description=description,
            amount=AMOUNT,
            currency="eur",
            metadata={"payment_intent_id": payment_intent_id},
        )

        # Create the invoice
        invoice = stripe.Invoice.create(
            customer=stripe_customer_id,
            auto_advance=True  # Automatically finalize the invoice
        )

        return invoice

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create-checkout-session/")
async def create_checkout_session(user=Depends(get_verified_user)):
    try:
        # Create a Stripe Checkout session
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'eur',
                    'product_data': {
                        'name': 'Credits',
                    },
                    'unit_amount': AMOUNT,
                },
                'quantity': 1,
            }],
            mode='payment',
            customer=user.stripe_customer_id if user.stripe_customer_id else None,
            customer_email=None if user.stripe_customer_id else user.email,
            customer_creation='always' if not user.stripe_customer_id else None,  # Always create a customer if they don't have one
            success_url=f'https://www.google.com',  # Frontend success page
            cancel_url=f'https://www.google.com',  # Frontend cancel page
            payment_intent_data={
                'metadata': {
                    'from_checkout_session': 'true'
                },
                'setup_future_usage': 'off_session'  # This tells Stripe to save the payment method
            }
        )
        return {"url": session.url}
    except Exception as e:
        print("ERROR:::: ", e)
        raise HTTPException(status_code=500, detail=str(e))


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

        # Handle Stripe events
        if event_type == "checkout.session.completed":
            if event_data.get("payment_status") == "paid":
                handle_checkout_session_completed(event_data)
                return

        elif event_type == "payment_intent.succeeded":
            handle_payment_intent_succeeded(event_data)
            return

        elif event_type == 'payment_method.attached':
            handle_payment_method_attached(event_data)
            return

        elif event_type == 'payment_method.detached':
            handle_payment_method_detached(event_data)
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
        customer_email = charges[0].get("billing_details", {}).get("email") if charges else None
        failure_reason = event_data.get("last_payment_error", {}).get("message", "Unknown reason")

        if not customer_email:
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
            "charged_amount": event_data.get("amount", 0),
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
    user_email = data["customer_details"]["email"]
    user = Users.get_user_by_email(user_email)

    try:
        # Save Stripe Customer ID if missing
        if user.stripe_customer_id is None:
            Users.update_user_by_id(user.id, {"stripe_customer_id": data["customer"]})

        # Update company credits
        company = Companies.get_company_by_id(user.company_id)

        Companies.add_credit_balance(user.company_id, CREDITS_TO_ADD)

        # Get payment method details and update card number
        payment_intent = stripe.PaymentIntent.retrieve(data["payment_intent"])
        if payment_intent.payment_method:
            payment_method = stripe.PaymentMethod.retrieve(payment_intent.payment_method)
            if payment_method.card:
                new_card_number = f"**** **** **** {payment_method.card.last4}"
                Companies.update_company_by_id(user.company_id, {
                    "credit_card_number": new_card_number,
                    "auto_recharge": True  # Enable auto-recharge by default when card is saved
                })

                # Set this payment method as the default for future payments
                stripe.Customer.modify(
                    data["customer"],
                    invoice_settings={
                        'default_payment_method': payment_intent.payment_method
                    }
                )

        create_and_finalize_invoice(
            stripe_customer_id=data["customer"],
            payment_intent_id=data["payment_intent"],
            description="Credits Purchase via Checkout"
        )

        # Log payment history
        payment_date = datetime.utcfromtimestamp(data["created"])
        payment_data = {
            "id": f"payment_{data['id']}",
            "stripe_transaction_id": data["id"],
            "company_id": company.id,
            "user_id": user.id,
            "description": "Credits Purchase",
            "charged_amount": data["amount_total"],
            "currency": data["currency"],
            "payment_status": data["payment_status"],
            "payment_method": "card",
            "payment_date": payment_date,
            "payment_metadata": data.get("metadata", {}),
        }

        StripePaymentHistories.log_payment(payment_data)

    except KeyError as e:
        raise Exception("Invalid data structure in checkout.session.completed event")
    except Exception as e:
        raise


def handle_payment_intent_succeeded(data):
    try:
        # Skip if this is from a checkout session - credits are handled there
        if data.get("metadata", {}).get("from_checkout_session"):
            return

        user = Users.get_user_by_stripe_customer_id(data["customer"])

        if not user:
            raise Exception(f"No user found with stripe customer id: {data['customer']}")

        # Update company credits
        credits_to_add = data.get("metadata", {}).get("credits_to_add", CREDITS_TO_ADD)  # Use metadata if available
        if isinstance(credits_to_add, str):
            credits_to_add = int(credits_to_add)  # Convert string to integer if needed

        Companies.add_credit_balance(user.company_id, credits_to_add)

        create_and_finalize_invoice(
            stripe_customer_id=user.stripe_customer_id,
            payment_intent_id=data["id"],
            description="Credits Purchase via Off-Session Payment"
        )

    except KeyError as e:
        raise Exception("Invalid data structure in payment_intent.succeeded event")
    except Exception as e:
        raise


@router.post("/charge-customer/")
async def charge_customer(user=Depends(get_verified_user)):
    try:
        if not user.stripe_customer_id:
            raise HTTPException(status_code=400, detail="User does not have a saved Stripe customer ID")

        customer = stripe.Customer.retrieve(user.stripe_customer_id)
        payment_method = customer.get("invoice_settings", {}).get("default_payment_method")

        if not payment_method:
            raise HTTPException(status_code=400, detail="No default payment method found for customer")

        payment_intent = stripe.PaymentIntent.create(
            amount=AMOUNT,
            currency='eur',
            customer=user.stripe_customer_id,
            payment_method=payment_method,
            off_session=True,
            confirm=True,
            metadata={
                "customer_email": user.email,
                "credits_to_add": CREDITS_TO_ADD
            }
        )

        return {"status": "success", "payment_intent": payment_intent}
    except stripe.error.CardError as e:
        raise HTTPException(status_code=400, detail=f"Card error: {e.user_message}")
    except Exception as e:
        print("ERROR:::: ", e)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/customer-billing-page/")
async def customer_billing_page(user=Depends(get_verified_user)):
    test_string = ''
    try:
        test_string += "got user\n"
        if not user.stripe_customer_id:
            test_string += "did not had strip customer id\n"
            data = stripe.Customer.create(
                name=user.first_name + " " + user.last_name,
                email=user.email,
            )
            user = Users.update_user_by_id(user.id, {"stripe_customer_id": data['id']})
            test_string += "updated the user\n"

        test_string += "fetch user again\n"
        # Create a Customer Portal session
        portal_session = stripe.billing_portal.Session.create(
            customer=user.stripe_customer_id,
            return_url=f"",
        )

        # Return the URL for the billing page
        return {"url": portal_session.url}
    except Exception as e:
        print("ERROR:::: ", e)
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "test_string": test_string,
                "user": user.dict() if user else None,
                "email": user.email
            }
        )

def handle_payment_method_detached(event_data):
    try:
        stripe_customer_id = event_data.get("customer")
        if not stripe_customer_id:
            print("Stripe Customer ID is missing from the event data.")
            return

        user = Users.get_user_by_stripe_customer_id(stripe_customer_id)
        if not user:
            print(f"User not found for Stripe Customer ID: {stripe_customer_id}")
            return

        new_card_number = None
        updated_company = Companies.update_company_by_id(user.company_id, {"auto_recharge": False, "credit_card_number": None})

        if updated_company:
            print(f"Updated card number for company {updated_company.name}: {new_card_number}")
        else:
            print(f"Failed to update card number for customer {stripe_customer_id}")

    except Exception as e:
        print(f"Error handling payment_method.detached: {e}")

def handle_payment_method_attached(event_data):
    try:
        # Skip if this is from a checkout session - card details are handled there
        if event_data.get("metadata", {}).get("from_checkout_session"):
            return

        stripe_customer_id = event_data.get("customer")
        if not stripe_customer_id:
            print("Stripe Customer ID is missing from the event data.")
            return

        # Get card details
        payment_method = stripe.PaymentMethod.retrieve(event_data.get("id"))
        if not payment_method or not payment_method.card:
            print("No card details found in payment method.")
            return

        last4 = payment_method.card.last4
        new_card_number = f"**** **** **** {last4}"

        # Find user and update company card details
        user = Users.get_user_by_stripe_customer_id(stripe_customer_id)
        if not user:
            print(f"No user found for Stripe customer ID: {stripe_customer_id}")
            return

        Companies.update_company_by_id(user.company_id, {
            "credit_card_number": new_card_number,
            "auto_recharge": True
        })

        # Set this payment method as the default for future payments
        stripe.Customer.modify(
            stripe_customer_id,
            invoice_settings={
                'default_payment_method': event_data.get("id")
            }
        )

        print(f"Updated card number for company ID {user.company_id}: {new_card_number}")

    except Exception as e:
        print(f"Error handling payment_method.attached: {e}")


class UpdateAutoRechargeRequest(BaseModel):
    auto_recharge: bool

@router.post("/update-auto-recharge/")
async def update_auto_recharge(request: UpdateAutoRechargeRequest, user=Depends(get_verified_user)):
    try:
        if request.auto_recharge and not Companies.get_company_by_id(user.company_id).credit_card_number:
            raise HTTPException(status_code=400, detail="Auto recharge can only be activated with stored credit card number")

        updated_company = Companies.update_auto_recharge(user.company_id, request.auto_recharge)

        if not updated_company:
            raise HTTPException(status_code=404, detail="Company not found or update failed.")

        return {"message": f"Auto-recharge updated successfully for company {updated_company.id}."}
    except Exception as e:
        print("ERROR:::: ", e)
        raise HTTPException(status_code=500, detail=str(e))
