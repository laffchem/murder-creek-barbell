"""
Management command to test Stripe webhook handlers without needing actual Stripe events.
"""
from django.core.management.base import BaseCommand
from accounts.views.webhooks import (
    _handle_subscription_created,
    _handle_subscription_updated,
    _handle_invoice_paid
)
from accounts.models import StripeCustomer
import time


class Command(BaseCommand):
    help = 'Test Stripe webhook handlers with sample data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--customer-id',
            type=str,
            help='Stripe customer ID to test with (optional, will use first customer if not provided)'
        )

    def handle(self, *args, **options):
        customer_id = options.get('customer_id')

        # Get customer from database
        if customer_id:
            try:
                stripe_customer = StripeCustomer.objects.get(stripe_customer_id=customer_id)
            except StripeCustomer.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'StripeCustomer with ID {customer_id} not found'))
                return
        else:
            stripe_customer = StripeCustomer.objects.first()
            if not stripe_customer:
                self.stdout.write(self.style.ERROR('No StripeCustomer records found in database'))
                return
            customer_id = stripe_customer.stripe_customer_id

        self.stdout.write(self.style.SUCCESS(f'Testing webhooks for customer: {customer_id}'))

        # Test subscription.created
        self.stdout.write('\n--- Testing subscription.created ---')
        subscription_data = {
            'id': 'sub_test_12345',
            'customer': customer_id,
            'status': 'active',
            'items': {
                'data': [
                    {
                        'price': {
                            'id': 'price_test_monthly'
                        }
                    }
                ]
            },
            'current_period_end': int(time.time()) + (30 * 24 * 60 * 60),  # 30 days from now
            'cancel_at_period_end': False
        }

        _handle_subscription_created(subscription_data)
        self.stdout.write(self.style.SUCCESS('✓ subscription.created handler executed'))

        # Test invoice.payment_succeeded
        self.stdout.write('\n--- Testing invoice.payment_succeeded ---')
        invoice_data = {
            'customer': customer_id,
            'payment_intent': 'pi_test_67890',
            'amount_paid': 2999,  # $29.99 in cents
            'currency': 'usd',
            'subscription': 'sub_test_12345',
            'description': 'Test monthly subscription',
            'hosted_invoice_url': 'https://invoice.stripe.com/test'
        }

        _handle_invoice_paid(invoice_data)
        self.stdout.write(self.style.SUCCESS('✓ invoice.payment_succeeded handler executed'))

        # Verify results
        self.stdout.write('\n--- Verification ---')
        stripe_customer.refresh_from_db()

        self.stdout.write(f'Subscription ID: {stripe_customer.stripe_subscription_id}')
        self.stdout.write(f'Subscription Status: {stripe_customer.subscription_status}')
        self.stdout.write(f'Subscription Plan: {stripe_customer.subscription_plan}')
        self.stdout.write(f'Period End: {stripe_customer.current_period_end}')

        payment_count = stripe_customer.user.payments.count()
        self.stdout.write(f'Total Payments: {payment_count}')

        if stripe_customer.stripe_subscription_id and payment_count > 0:
            self.stdout.write(self.style.SUCCESS('\n✓ Webhook handlers are working correctly!'))
        else:
            self.stdout.write(self.style.WARNING('\n⚠ Some data may not have been saved. Check logs for errors.'))
