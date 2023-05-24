from fastapi import APIRouter, Request, Depends
from app.services.postgres_db import add_user_content_source, get_content_sources, get_all_content_sources, get_stripe_price_id, get_subscription_id, remove_user_content_source, fetch_user
from app.services.stripe import cancel_subscription, get_stripe_product, get_subscription_intent
from app.utils import decode_access_token
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import JSONResponse
from fastapi import HTTPException
from app.authentication.authenticate import authenticate

router = APIRouter()


def get_token(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())) -> str:
    token = credentials.credentials
    return decode_access_token(token)


@router.get('/content_sources')
async def content_sources(payload: dict = Depends(authenticate)):
    return get_content_sources()


@router.get('/user_content_sources')
async def user_content_sources(request: Request, token: str = Depends(get_token)):
    user_id = fetch_user(token)[0][0]
    return get_all_content_sources(user_id)


@router.post('/subscribe_content_source')
async def subscribe_content_source(request: Request, token: str = Depends(get_token)):
    user_id = fetch_user(token)[0][0]
    data = await request.json()
    response = add_user_content_source(
        user_id, data['content_source_id'], data['stripe_customer_id'], data['stripe_payment_method_id'], data['subscription_id'])
    if response:
        return JSONResponse(
            status_code=200,
            content={'status': "success",
                     "message": "Subscribed to content successfully!"}
        )
    else:
        raise HTTPException(
            status_code=400,
            detail={"status": "failure", "error": "Something went wrong!"}
        )


@router.delete('/unsubscribe_content_source')
async def unsubscribe_content_source(request: Request, token: str = Depends(get_token)):
    data = await request.json()
    user_id = fetch_user(token)[0][0]
    subscription_id = get_subscription_id(user_id, data['content_source_id'])
    is_canceled = cancel_subscription(subscription_id)
    if is_canceled is None:
        raise HTTPException(
            status_code=400,
            detail={"status": "failure", "error": "Something went wrong!"}
        )

    response = remove_user_content_source(
        user_id, data['content_source_id'])

    if response:
        return get_all_content_sources(user_id)
    else:
        raise HTTPException(
            status_code=400,
            detail={"status": "failure", "error": "Something went wrong!"}
        )


@router.get('/stripe_product_details')
async def stripe_product_for_content_source(content_source_id: str):
    stripe_price_id = get_stripe_price_id(content_source_id)
    product = get_stripe_product(stripe_price_id)
    return {'product': product}


@router.get('/subscription_intent')
async def subscription_intent(price_id: str, token: str = Depends(get_token)):
    subscription_intent = get_subscription_intent(price_id, token)
    return subscription_intent
