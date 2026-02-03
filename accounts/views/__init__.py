"""
Accounts views package.
Re-exports all views to maintain backwards compatibility with urls.py.
"""
# Account views
from .account import dashboard, billing, settings

# Checkout views
from .checkout import (
    create_checkout_session,
    checkout_success,
    checkout_cancel,
    create_customer_portal_session
)

# Subscription views
from .subscription import cancel_subscription

# Webhook views
from .webhooks import stripe_webhook

__all__ = [
    # Account
    'dashboard',
    'billing',
    'settings',
    # Checkout
    'create_checkout_session',
    'checkout_success',
    'checkout_cancel',
    'create_customer_portal_session',
    # Subscription
    'cancel_subscription',
    # Webhooks
    'stripe_webhook',
]
