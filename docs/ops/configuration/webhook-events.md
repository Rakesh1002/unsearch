# 📋 Webhook Events Explained

## Why Each Event is Important for UnSearch API

### 🔄 **Subscription Lifecycle Events**

| Event | Purpose | What it does in your app |
|-------|---------|-------------------------|
| `customer.subscription.created` | New subscription | Creates subscription record, activates user plan |
| `customer.subscription.updated` | Plan changes, renewals | Updates limits, plan details, billing cycle |  
| `customer.subscription.deleted` | Cancellations | Deactivates subscription, reverts to free plan |

### 💰 **Payment Events**

| Event | Purpose | What it does in your app |
|-------|---------|-------------------------|
| `invoice.paid` | Successful payment | Confirms payment, extends subscription period |
| `invoice.payment_failed` | Failed payment | Handles dunning, may suspend account |
| `payment_intent.succeeded` | One-time payments | Processes credits, upgrades, etc. |

### 🎯 **Customer Events**  

| Event | Purpose | What it does in your app |
|-------|---------|-------------------------|
| `payment_method.attached` | New card added | Updates default payment method |
| `checkout.session.completed` | Purchase completed | Links payment to user account |

## 🛡️ Security Features

Your webhook handler includes:

✅ **Signature Verification**: Validates requests come from Stripe
✅ **Idempotency**: Prevents duplicate event processing  
✅ **Event Logging**: Tracks all webhook events for debugging
✅ **Error Handling**: Graceful failure handling

## 🔍 Monitoring Webhook Health

Check webhook status:
- **Dashboard**: https://dashboard.stripe.com/test/webhooks  
- **Logs**: Your app logs webhook processing
- **CLI**: `stripe events list` to see recent events

## ⚡ Testing Tips

```bash
# Test all critical events
stripe trigger customer.subscription.created
stripe trigger customer.subscription.updated  
stripe trigger invoice.payment_succeeded
stripe trigger invoice.payment_failed
```

Your app will automatically:
- Create/update user subscriptions
- Adjust API limits and features
- Handle payment failures gracefully
- Maintain accurate billing records
