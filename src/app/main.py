from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.subscriptions import router as subscriptions_router
from app.api.user import router as user_router
from app.middleware.timing import RequestTimingMiddleware

app = FastAPI(title="Subscription Tracker API")
app.add_middleware(RequestTimingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Accept", "Authorization", "Content-Type"],
)
app.include_router(subscriptions_router)
app.include_router(user_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
