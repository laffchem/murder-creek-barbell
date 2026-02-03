"""Stripe checkout session and payment flow views."""
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from .stripe_client import stripe
from ..models import StripeCustomer


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
