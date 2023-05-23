import os
import stripe
import dotenv

from app.services.postgres_db import fetch_user

dotenv.load_dotenv()
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')


def get_stripe_product(price_id):
    price = stripe.Price.retrieve(price_id)
    product = stripe.Product.retrieve(price['product'])
    return {
        'price_id': price['id'],
        'product_id': product['id'],
        'name': product['name'],
        'description': product['description'],
        'amount': price['unit_amount']/100,
    }


def get_subscription_intent(price_id, email):
    customer = create_customer(email)
    subscription = stripe.Subscription.create(
        customer=customer.id,
        items=[{
            'price': price_id,
        }],
        payment_behavior='default_incomplete',
        payment_settings={'save_default_payment_method': 'on_subscription'},
        expand=['latest_invoice.payment_intent'],
    )
    return {'subscription_id': subscription.id, 'client_secret': subscription.latest_invoice.payment_intent.client_secret, 'customer_id': customer.id}


def create_customer(email):
    user = fetch_user(email)[0]
    customer = stripe.Customer.create(
        email=email,
        name=f"{user[3]} {user[4]}",
    )
    return customer


def cancel_subscription(subscription_id):
    subscription = stripe.Subscription.delete(subscription_id)
    if subscription:
        return True
    return None
