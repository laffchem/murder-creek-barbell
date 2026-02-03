"""Subscription management views."""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .stripe_client import stripe
from ..models import StripeCustomer
from ..forms import CancelSubscriptionForm


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
                # Show validation error if form is invalid
                messages.error(request, 'Please confirm the checkbox to cancel your subscription.')
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
