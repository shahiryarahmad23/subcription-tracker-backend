from fastapi import FastAPI

from app.api.subscriptions import router as subscriptions_router
from app.api.user import router as user_router
from app.middleware.timing import RequestTimingMiddleware

app = FastAPI(title="Subscription Tracker API")
app.add_middleware(RequestTimingMiddleware)
app.include_router(subscriptions_router)
app.include_router(user_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
