from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Account dashboard
    path('', views.dashboard, name='dashboard'),

    # Billing and payments
    path('billing/', views.billing, name='billing'),

    # Settings
    path('settings/', views.settings, name='settings'),

    # Stripe checkout
    path('create-checkout-session/', views.create_checkout_session, name='create_checkout_session'),
    path('checkout/success/', views.checkout_success, name='checkout_success'),
    path('checkout/cancel/', views.checkout_cancel, name='checkout_cancel'),

    # Stripe customer portal
    path('customer-portal/', views.create_customer_portal_session, name='customer_portal'),

    # Subscription management
    path('cancel-subscription/', views.cancel_subscription, name='cancel_subscription'),

    # Webhooks
    path('webhook', views.stripe_webhook, name='stripe_webhook'),
]
