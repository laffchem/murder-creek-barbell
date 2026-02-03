"""Stripe API client initialization and shared utilities."""
from django.conf import settings
import stripe
import logging

# Initialize logger
logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

# Export stripe module for use by other views
__all__ = ['stripe', 'logger']
