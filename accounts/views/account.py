"""Account management views: dashboard, billing, settings."""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ..models import StripeCustomer
from ..forms import UpdateProfileForm


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
