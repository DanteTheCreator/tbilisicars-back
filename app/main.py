from __future__ import annotations

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="TbilisiCars API", version="1.0.0")

# CORS middleware - must be added BEFORE any routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://127.0.0.1:3000",
        "https://tbilisicars.live"
    ],  # Frontend URLs
    allow_credentials=True,  # Allow credentials for auth
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

@app.get("/health")
async def health():
    return {"status": "ok"}

# Import and mount routes AFTER middleware
from .routes import (
    bookings, users, vehicles, locations, damages, documents,
    payments, reviews, promos, booking_extras,
    booking_promos, vehicle_prices, extras
)

from app.routes import api_router

app.include_router(api_router)
