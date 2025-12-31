from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """Custom user manager for email-based authentication."""

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular user with the given email and password."""
        if not email:
            raise ValueError(_('The Email field must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a superuser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Custom user model that uses email instead of username."""

    username = None  # Remove username field
    email = models.EmailField(_('email address'), unique=True)
    first_name = models.CharField(_('first name'), max_length=150)
    last_name = models.CharField(_('last name'), max_length=150)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = UserManager()

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def __str__(self):
        return self.email

    def get_full_name(self):
        """Return the first_name plus the last_name, with a space in between."""
        return f"{self.first_name} {self.last_name}".strip()


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
