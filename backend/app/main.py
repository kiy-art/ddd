from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import admin, products

settings = get_settings()

app = FastAPI(title="Golf Deals API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    # No cookies are used (admin auth is a Bearer token in a header), so
    # credentials aren't needed and origins can be a plain allow-list.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


@app.get("/")
def root():
    return {"service": "golf-deals-api", "status": "ok"}
