# Murder Creek Barbell - Account System Setup Guide

## Overview
Your gym website now has a complete authentication and payment system with:
- ✅ Magic link email login (no passwords!)
- ✅ Email, first name, last name signup
- ✅ Stripe integration for subscriptions and one-time payments
- ✅ Account dashboard with subscription status
- ✅ Payment history tracking
- ✅ Stripe Customer Portal integration
- ✅ Self-service subscription cancellation
- ✅ Dark theme matching your site aesthetic

## Quick Start

### 1. Set Up Stripe

1. **Create a Stripe account** at https://stripe.com (if you don't have one)
2. **Get your API keys** from https://dashboard.stripe.com/apikeys
   - Copy your **Publishable key** (starts with `pk_test_`)
   - Copy your **Secret key** (starts with `sk_test_`)

3. **Create a product and price**:
   - Go to https://dashboard.stripe.com/products
   - Click "Add product"
   - Name it "Gym Membership" (or whatever you prefer)
   - Set your monthly price
   - Copy the **Price ID** (starts with `price_`)

4. **Set up webhooks**:
   - Go to https://dashboard.stripe.com/webhooks
   - Click "Add endpoint"
   - URL: `https://yourdomain.com/account/webhook/`
   - Select events to listen for:
     - `customer.subscription.created`
     - `customer.subscription.updated`
     - `customer.subscription.deleted`
     - `invoice.payment_succeeded`
     - `invoice.payment_failed`
   - Copy the **Webhook signing secret** (starts with `whsec_`)

### 2. Configure Environment Variables

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your Stripe keys:
   ```
   STRIPE_PUBLISHABLE_KEY=pk_test_your_key_here
   STRIPE_SECRET_KEY=sk_test_your_key_here
   STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here
   ```

3. **Important**: Never commit your `.env` file (already in `.gitignore`)

### 3. Test the System

1. **Start your development server**:
   ```bash
   uv run manage.py runserver
   ```

2. **Create a test user**:
   - Go to http://localhost:8000/accounts/signup/
   - Fill in your email, first name, last name
   - Check your console for the magic link email
   - Click the link to verify your email

3. **Test the magic link login**:
   - Go to http://localhost:8000/accounts/login/
   - Enter your email
   - Check console for the magic link
   - Click to login

4. **Access your account**:
   - Click on your name in the navbar
   - Explore Dashboard, Billing, Settings

## How It Works

### Authentication Flow (Magic Link)

**For New Users (Signup)**:
1. User enters email, first name, last name on signup page
2. Django Allauth sends verification email with confirmation link
3. User clicks the link in email
4. Email is confirmed and user is automatically logged in - no password needed!

**For Returning Users (Login)**:
1. User enters email on login page
2. Django Allauth sends magic link via email
3. User clicks link in email
4. Automatically logged in - no password needed!

**Development**: Emails appear in your console
**Production**: Configure SMTP in `.env` (see `.env.example`)

**Note**: The setting `ACCOUNT_CONFIRM_EMAIL_ON_GET = True` ensures that clicking the email confirmation link automatically confirms and logs in the user without requiring an additional button click.

### Stripe Integration

#### Subscription Flow
1. User clicks "Start Membership" on dashboard
2. Redirected to Stripe Checkout (hosted by Stripe)
3. Enters payment info securely on Stripe
4. Webhooks update subscription status in your database
5. User sees active subscription on dashboard

#### Payment Management
- **Update payment method**: Via Stripe Customer Portal
- **Cancel subscription**: Self-service cancellation (cancels at period end)
- **Payment history**: All payments tracked in database

### Database Models

**User**
- Email (unique, used for login)
- First name, last name
- No username field

**StripeCustomer**
- Linked to User (one-to-one)
- Stores Stripe customer ID
- Tracks subscription status, plan, billing dates
- `has_active_subscription` property

**Payment**
- Linked to User (many-to-one)
- Tracks all payments (subscription & one-time)
- Stores amount, status, invoice URL

## URLs

- `/accounts/signup/` - Sign up
- `/accounts/login/` - Login
- `/accounts/logout/` - Logout
- `/account/` - Dashboard
- `/account/billing/` - Payment history
- `/account/settings/` - Account settings
- `/account/customer-portal/` - Stripe Customer Portal
- `/account/cancel-subscription/` - Cancel membership
- `/account/webhook/` - Stripe webhook endpoint

## Customization

### Adding a "Join Now" Button

In your homepage ([templates/cotton/hero.html:14](templates/cotton/hero.html#L14)), you can update the "Join Now" button:

```html
<a href="{% url 'accounts:create_checkout_session' %}" class="btn btn-lg btn-light">
    Join Now
</a>
```

### Stripe Checkout Session

To create a checkout session, you need to pass the Stripe Price ID. Update [accounts/views.py:create_checkout_session](accounts/views.py:83) or create a form that includes the price ID.

Example button with hidden form:
```html
<form method="post" action="{% url 'accounts:create_checkout_session' %}">
    {% csrf_token %}
    <input type="hidden" name="price_id" value="price_YOUR_STRIPE_PRICE_ID">
    <input type="hidden" name="payment_type" value="subscription">
    <button type="submit" class="btn btn-lg btn-light">Join Now - $70/mo</button>
</form>
```

### Styling

All templates use your existing dark theme:
- Black backgrounds (`bg-black`, `bg-dark`)
- Red accents (via `--accent-color` CSS variable)
- Ubuntu Condensed font for headings
- Bootstrap 5 components
- Bootstrap Icons

To change the accent color, edit [static/css/styles.css:2](static/css/styles.css#L2):
```css
--accent-color: #dc3545; /* Change this color */
```

## Production Checklist

Before deploying to production:

- [ ] Set up real email backend (SMTP) in `.env`
- [ ] Use Stripe live keys (not test keys)
- [ ] Set `DEBUG=False` in settings
- [ ] Update `ALLOWED_HOSTS` in settings
- [ ] Set up HTTPS (required for Stripe)
- [ ] Configure webhook URL with your domain
- [ ] Update Stripe Customer Portal settings
- [ ] Test full signup → payment → cancellation flow
- [ ] Set up proper `SECRET_KEY` in `.env`

## Troubleshooting

### Magic links not working?
- Check console output for email content (development)
- Verify `EMAIL_BACKEND` is set correctly
- Ensure email verification is enabled in settings

### Stripe checkout not working?
- Verify API keys are correct in `.env`
- Check that price ID is valid
- Look for errors in console/logs

### Webhooks failing?
- Verify webhook secret is correct
- Check webhook endpoint is accessible
- Review Stripe dashboard webhook logs

### Database issues?
```bash
uv run manage.py makemigrations
uv run manage.py migrate
```

## Support

Need help? Check:
- [Django Allauth Documentation](https://django-allauth.readthedocs.io/)
- [Stripe Documentation](https://stripe.com/docs)
- [Bootstrap 5 Documentation](https://getbootstrap.com/docs/5.3/)

## What's Next?

Consider adding:
- Multiple membership tiers
- Drop-in day passes (one-time payments)
- Member check-in system
- Class schedules
- Admin dashboard for member management
