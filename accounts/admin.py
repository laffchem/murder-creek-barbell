from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, StripeCustomer, Payment


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin configuration for custom User model."""

    list_display = ('email', 'first_name', 'last_name', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active', 'date_joined')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('-date_joined',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )


@admin.register(StripeCustomer)
class StripeCustomerAdmin(admin.ModelAdmin):
    """Admin configuration for StripeCustomer model."""

    list_display = (
        'user',
        'stripe_customer_id',
        'subscription_status',
        'subscription_plan',
        'current_period_end',
        'cancel_at_period_end'
    )
    list_filter = ('subscription_status', 'cancel_at_period_end', 'created_at')
    search_fields = ('user__email', 'stripe_customer_id', 'stripe_subscription_id')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('User', {'fields': ('user',)}),
        ('Stripe Information', {
            'fields': ('stripe_customer_id', 'stripe_subscription_id')
        }),
        ('Subscription Details', {
            'fields': (
                'subscription_status',
                'subscription_plan',
                'current_period_end',
                'cancel_at_period_end'
            )
        }),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """Admin configuration for Payment model."""

    list_display = (
        'user',
        'amount',
        'currency',
        'status',
        'payment_type',
        'created_at'
    )
    list_filter = ('status', 'payment_type', 'currency', 'created_at')
    search_fields = ('user__email', 'stripe_payment_id', 'description')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'

    fieldsets = (
        ('User', {'fields': ('user',)}),
        ('Payment Information', {
            'fields': ('stripe_payment_id', 'amount', 'currency', 'status', 'payment_type')
        }),
        ('Details', {
            'fields': ('description', 'invoice_url')
        }),
        ('Timestamp', {'fields': ('created_at',)}),
    )
