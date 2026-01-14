from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routers import accounts, pages, sync, transactions

app = FastAPI(title="Portfolio Tracker")

templates = Jinja2Templates(directory="app/templates")

# Routers
app.include_router(pages.router)
app.include_router(accounts.router, prefix="/api/accounts", tags=["accounts"])
app.include_router(sync.router, prefix="/api/sync", tags=["sync"])
app.include_router(transactions.router, prefix="/transactions", tags=["transactions"])


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
