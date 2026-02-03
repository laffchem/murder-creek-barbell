from django.db import models
from django.utils.translation import gettext_lazy as _
from .user import User


class StripeCustomer(models.Model):
    """Model to track Stripe customer and subscription data."""

    SUBSCRIPTION_STATUS_CHOICES = [
        ('active', 'Active'),
        ('canceled', 'Canceled'),
        ('past_due', 'Past Due'),
        ('incomplete', 'Incomplete'),
        ('trialing', 'Trialing'),
        ('unpaid', 'Unpaid'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='stripe_customer'
    )
    stripe_customer_id = models.CharField(
        max_length=255,
        unique=True,
        help_text='Stripe customer ID'
    )
    stripe_subscription_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='Stripe subscription ID'
    )
    subscription_status = models.CharField(
        max_length=20,
        choices=SUBSCRIPTION_STATUS_CHOICES,
        blank=True,
        null=True
    )
    subscription_plan = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='Name of the subscription plan'
    )
    current_period_end = models.DateTimeField(
        blank=True,
        null=True,
        help_text='Current subscription period end date'
    )
    cancel_at_period_end = models.BooleanField(
        default=False,
        help_text='Whether the subscription will cancel at period end'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Stripe Customer'
        verbose_name_plural = 'Stripe Customers'

    def __str__(self):
        return f"{self.user.email} - {self.stripe_customer_id}"

    @property
    def has_active_subscription(self):
        """Check if the customer has an active subscription."""
        return self.subscription_status in ['active', 'trialing']


class Payment(models.Model):
    """Model to track payment history."""

    PAYMENT_TYPE_CHOICES = [
        ('subscription', 'Subscription'),
        ('one_time', 'One-Time Payment'),
    ]

    STATUS_CHOICES = [
        ('succeeded', 'Succeeded'),
        ('pending', 'Pending'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    stripe_payment_id = models.CharField(
        max_length=255,
        unique=True,
        help_text='Stripe payment intent or charge ID'
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Payment amount'
    )
    currency = models.CharField(
        max_length=3,
        default='usd',
        help_text='Payment currency (e.g., USD, EUR)'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    payment_type = models.CharField(
        max_length=20,
        choices=PAYMENT_TYPE_CHOICES,
        default='one_time'
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text='Payment description'
    )
    invoice_url = models.URLField(
        blank=True,
        null=True,
        help_text='Stripe invoice URL'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - ${self.amount} ({self.status})"
