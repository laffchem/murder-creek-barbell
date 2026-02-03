"""Stripe webhook handlers and event processors."""
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from datetime import datetime, timezone
import stripe
from ..models import StripeCustomer, Payment
from .stripe_client import logger


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """Handle Stripe webhooks."""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    logger.info("Received Stripe webhook request")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError as e:
        logger.error(f"Webhook error: Invalid payload - {str(e)}")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Webhook error: Invalid signature - {str(e)}")
        return HttpResponse(status=400)

    event_type = event['type']
    logger.info(f"Processing webhook event: {event_type}")

    # Handle the event
    if event_type == 'customer.subscription.created':
        subscription = event['data']['object']
        _handle_subscription_created(subscription)

    elif event_type == 'customer.subscription.updated':
        subscription = event['data']['object']
        _handle_subscription_updated(subscription)

    elif event_type == 'customer.subscription.deleted':
        subscription = event['data']['object']
        _handle_subscription_deleted(subscription)

    elif event_type == 'invoice.payment_succeeded':
        invoice = event['data']['object']
        _handle_invoice_paid(invoice)

    elif event_type == 'invoice.payment_failed':
        invoice = event['data']['object']
        _handle_invoice_payment_failed(invoice)

    else:
        logger.info(f"Unhandled webhook event type: {event_type}")

    logger.info(f"Successfully processed webhook event: {event_type}")
    return HttpResponse(status=200)


def _handle_subscription_created(subscription):
    """Handle subscription created event."""
    customer_id = subscription['customer']
    subscription_id = subscription['id']

    logger.info(f"Processing subscription.created for customer {customer_id}, subscription {subscription_id}")

    try:
        stripe_customer = StripeCustomer.objects.get(stripe_customer_id=customer_id)

        stripe_customer.stripe_subscription_id = subscription_id
        stripe_customer.subscription_status = subscription['status']
        stripe_customer.subscription_plan = subscription['items']['data'][0]['price']['id']

        # Convert Unix timestamp to datetime
        # Use cancel_at if subscription is being canceled, otherwise use current_period_end
        if subscription['cancel_at_period_end'] and subscription.get('cancel_at'):
            period_end_timestamp = subscription['cancel_at']
        else:
            period_end_timestamp = subscription.get('current_period_end')

        if period_end_timestamp:
            stripe_customer.current_period_end = datetime.fromtimestamp(
                period_end_timestamp,
                tz=timezone.utc
            )

        stripe_customer.cancel_at_period_end = subscription['cancel_at_period_end']
        stripe_customer.save()

        logger.info(f"Successfully updated subscription for customer {customer_id}")
    except StripeCustomer.DoesNotExist:
        logger.error(f"StripeCustomer not found for customer_id: {customer_id}")
    except Exception as e:
        logger.error(f"Error handling subscription.created for {customer_id}: {str(e)}")


def _handle_subscription_updated(subscription):
    """Handle subscription updated event."""
    customer_id = subscription['customer']
    subscription_id = subscription['id']

    logger.info(f"Processing subscription.updated for customer {customer_id}, subscription {subscription_id}")

    try:
        stripe_customer = StripeCustomer.objects.get(stripe_customer_id=customer_id)

        stripe_customer.subscription_status = subscription['status']

        # Convert Unix timestamp to datetime
        # Use cancel_at if subscription is being canceled, otherwise use current_period_end
        if subscription['cancel_at_period_end'] and subscription.get('cancel_at'):
            period_end_timestamp = subscription['cancel_at']
        else:
            period_end_timestamp = subscription.get('current_period_end')

        if period_end_timestamp:
            stripe_customer.current_period_end = datetime.fromtimestamp(
                period_end_timestamp,
                tz=timezone.utc
            )

        stripe_customer.cancel_at_period_end = subscription['cancel_at_period_end']
        stripe_customer.save()

        logger.info(f"Successfully updated subscription for customer {customer_id}")
    except StripeCustomer.DoesNotExist:
        logger.error(f"StripeCustomer not found for customer_id: {customer_id}")
    except Exception as e:
        logger.error(f"Error handling subscription.updated for {customer_id}: {str(e)}")


def _handle_subscription_deleted(subscription):
    """Handle subscription deleted event."""
    customer_id = subscription['customer']
    subscription_id = subscription['id']

    logger.info(f"Processing subscription.deleted for customer {customer_id}, subscription {subscription_id}")

    try:
        stripe_customer = StripeCustomer.objects.get(stripe_customer_id=customer_id)

        stripe_customer.subscription_status = 'canceled'
        stripe_customer.stripe_subscription_id = None
        stripe_customer.save()

        logger.info(f"Successfully marked subscription as canceled for customer {customer_id}")
    except StripeCustomer.DoesNotExist:
        logger.error(f"StripeCustomer not found for customer_id: {customer_id}")
    except Exception as e:
        logger.error(f"Error handling subscription.deleted for {customer_id}: {str(e)}")


def _handle_invoice_paid(invoice):
    """Handle invoice payment succeeded event."""
    customer_id = invoice['customer']
    # Use invoice ID as payment ID (payment_intent field removed in Stripe API 2025-03-31)
    payment_id = invoice['id']

    logger.info(f"Processing invoice.payment_succeeded for customer {customer_id}, payment {payment_id}")

    try:
        stripe_customer = StripeCustomer.objects.get(stripe_customer_id=customer_id)

        # Use get_or_create to handle duplicate webhooks
        payment, created = Payment.objects.get_or_create(
            stripe_payment_id=payment_id,
            defaults={
                'user': stripe_customer.user,
                'amount': invoice['amount_paid'] / 100,  # Convert from cents
                'currency': invoice['currency'],
                'status': 'succeeded',
                'payment_type': 'subscription' if invoice.get('subscription') else 'one_time',
                'description': invoice.get('description', ''),
                'invoice_url': invoice.get('hosted_invoice_url', '')
            }
        )

        if created:
            logger.info(f"Created new payment record for {payment_id}")
        else:
            logger.info(f"Payment record already exists for {payment_id}, skipping duplicate")

    except StripeCustomer.DoesNotExist:
        logger.error(f"StripeCustomer not found for customer_id: {customer_id}")
    except Exception as e:
        logger.error(f"Error handling invoice.payment_succeeded for {customer_id}: {str(e)}")


def _handle_invoice_payment_failed(invoice):
    """Handle invoice payment failed event."""
    customer_id = invoice['customer']
    # Use invoice ID as payment ID (payment_intent field removed in Stripe API 2025-03-31)
    payment_id = invoice['id']

    logger.info(f"Processing invoice.payment_failed for customer {customer_id}, payment {payment_id}")

    try:
        stripe_customer = StripeCustomer.objects.get(stripe_customer_id=customer_id)

        # Update subscription status
        stripe_customer.subscription_status = 'past_due'
        stripe_customer.save()

        # Use get_or_create to handle duplicate webhooks
        payment, created = Payment.objects.get_or_create(
            stripe_payment_id=payment_id,
            defaults={
                'user': stripe_customer.user,
                'amount': invoice['amount_due'] / 100,
                'currency': invoice['currency'],
                'status': 'failed',
                'payment_type': 'subscription' if invoice.get('subscription') else 'one_time',
                'description': invoice.get('description', ''),
                'invoice_url': invoice.get('hosted_invoice_url', '')
            }
        )

        if created:
            logger.info(f"Created new failed payment record for {payment_id}")
        else:
            logger.info(f"Failed payment record already exists for {payment_id}, skipping duplicate")

    except StripeCustomer.DoesNotExist:
        logger.error(f"StripeCustomer not found for customer_id: {customer_id}")
    except Exception as e:
        logger.error(f"Error handling invoice.payment_failed for {customer_id}: {str(e)}")
