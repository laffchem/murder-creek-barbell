from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.db import IntegrityError
from datetime import datetime, timezone
import stripe
import json
import logging
from .models import StripeCustomer, Payment
from .forms import UpdateProfileForm, CancelSubscriptionForm

# Initialize logger
logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


@login_required
def dashboard(request):
    """Account dashboard view."""
    user = request.user
    stripe_customer = None
    has_subscription = False

    try:
        stripe_customer = user.stripe_customer
        has_subscription = stripe_customer.has_active_subscription
    except StripeCustomer.DoesNotExist:
        pass

    context = {
        'stripe_customer': stripe_customer,
        'has_subscription': has_subscription,
    }
    return render(request, 'accounts/dashboard.html', context)


@login_required
def billing(request):
    """Billing and payment history view."""
    user = request.user
    payments = user.payments.all()[:20]  # Last 20 payments

    try:
        stripe_customer = user.stripe_customer
    except StripeCustomer.DoesNotExist:
        stripe_customer = None

    context = {
        'payments': payments,
        'stripe_customer': stripe_customer,
    }
    return render(request, 'accounts/billing.html', context)


@login_required
def settings(request):
    """Account settings view."""
    user = request.user

    if request.method == 'POST':
        form = UpdateProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:settings')
    else:
        form = UpdateProfileForm(instance=user)

    try:
        stripe_customer = user.stripe_customer
    except StripeCustomer.DoesNotExist:
        stripe_customer = None

    context = {
        'form': form,
        'stripe_customer': stripe_customer,
    }
    return render(request, 'accounts/settings.html', context)


@login_required
@require_POST
def create_checkout_session(request):
    """Create a Stripe checkout session for subscription or one-time payment."""
    try:
        # Get or create Stripe customer
        stripe_customer = None
        try:
            stripe_customer = request.user.stripe_customer
            customer_id = stripe_customer.stripe_customer_id
        except StripeCustomer.DoesNotExist:
            # Create new Stripe customer
            customer = stripe.Customer.create(
                email=request.user.email,
                name=request.user.get_full_name(),
            )
            customer_id = customer.id
            # Save to database
            stripe_customer = StripeCustomer.objects.create(
                user=request.user,
                stripe_customer_id=customer_id
            )

        # Get price ID from request (you'll need to create products/prices in Stripe dashboard)
        price_id = 'price_1STl45Ru9ccavkk7c9LOo0rd'  # e.g., 'price_xxx' from Stripe
        payment_type = request.POST.get('payment_type', 'subscription')  # 'subscription' or 'payment'

        # Create checkout session
        if payment_type == 'subscription':
            checkout_session = stripe.checkout.Session.create(
                customer=customer_id,
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=request.build_absolute_uri('/account/checkout/success/'),
                cancel_url=request.build_absolute_uri('/account/checkout/cancel/'),
            )
        else:
            checkout_session = stripe.checkout.Session.create(
                customer=customer_id,
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='payment',
                success_url=request.build_absolute_uri('/account/checkout/success/'),
                cancel_url=request.build_absolute_uri('/account/checkout/cancel/'),
            )

        return redirect(checkout_session.url)

    except Exception as e:
        messages.error(request, f'Error creating checkout session: {str(e)}')
        return redirect('accounts:dashboard')


@login_required
def checkout_success(request):
    """Checkout success page."""
    messages.success(request, 'Payment successful! Thank you for your purchase.')
    return redirect('accounts:dashboard')


@login_required
def checkout_cancel(request):
    """Checkout canceled page."""
    messages.info(request, 'Checkout was canceled.')
    return redirect('accounts:dashboard')


@login_required
def create_customer_portal_session(request):
    """Create a Stripe customer portal session."""
    try:
        stripe_customer = request.user.stripe_customer
        portal_session = stripe.billing_portal.Session.create(
            customer=stripe_customer.stripe_customer_id,
            return_url=request.build_absolute_uri('/account/settings/'),
        )
        return redirect(portal_session.url)
    except StripeCustomer.DoesNotExist:
        messages.error(request, 'No customer account found.')
        return redirect('accounts:settings')
    except Exception as e:
        messages.error(request, f'Error accessing customer portal: {str(e)}')
        return redirect('accounts:settings')


@login_required
def cancel_subscription(request):
    """Cancel user subscription."""
    try:
        stripe_customer = request.user.stripe_customer

        if not stripe_customer.stripe_subscription_id:
            messages.error(request, 'No active subscription found.')
            return redirect('accounts:dashboard')

        if request.method == 'POST':
            form = CancelSubscriptionForm(request.POST)
            if form.is_valid():
                # Cancel subscription at period end
                stripe.Subscription.modify(
                    stripe_customer.stripe_subscription_id,
                    cancel_at_period_end=True
                )
                stripe_customer.cancel_at_period_end = True
                stripe_customer.save()

                messages.success(request, 'Subscription will be canceled at the end of the billing period.')
                return redirect('accounts:dashboard')
        else:
            form = CancelSubscriptionForm()

        context = {
            'form': form,
            'stripe_customer': stripe_customer,
        }
        return render(request, 'accounts/cancel_subscription.html', context)

    except StripeCustomer.DoesNotExist:
        messages.error(request, 'No subscription found.')
        return redirect('accounts:dashboard')
    except Exception as e:
        messages.error(request, f'Error canceling subscription: {str(e)}')
        return redirect('accounts:dashboard')


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
        period_end_timestamp = subscription['current_period_end']
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
        period_end_timestamp = subscription['current_period_end']
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
    payment_id = invoice['payment_intent'] or invoice['id']

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
    payment_id = invoice['payment_intent'] or invoice['id']

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
