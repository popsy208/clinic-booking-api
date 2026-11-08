from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app import models
from app.database import Base, engine
from app.routes.bookings import router as bookings_router
from app.routes.slots import router as slots_router
from app.routes.web import router as web_router

app = FastAPI(
    title="Koya Clinic Booking API",
    description="API for viewing and booking clinic appointment slots.",
    version="1.0.0",
)
@app.on_event("startup")
def create_tables():
    Base.metadata.create_all(bind=engine)


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": str(exc.detail)},
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"error": "Invalid or missing request data"},
    )


app.include_router(slots_router)
app.include_router(bookings_router)
app.include_router(web_router)
app.mount("/", StaticFiles(directory="static", html=True), name="static")