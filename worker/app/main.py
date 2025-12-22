from __future__ import annotations

from typing import List

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from . import models
from .config import get_settings
from .db import Base, engine, get_db
from .schemas import (
    
    ConversionRequest,
    ConversionResponse,
    CurrencyConversionDetail,
    CurrencyDetectionRequest,
    CurrencyDetectionResponse,
    DetectedCurrency,
    HistoryResponse,
)
from .services import analyzer
from .services.currency import CurrencyServiceError, convert_currency
from .services.currency_extractor import extract_currency_mentions

settings = get_settings()

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}





@app.post("/convert", response_model=ConversionResponse, status_code=status.HTTP_201_CREATED)
def convert(
    payload: ConversionRequest, session: Session = Depends(get_db)
) -> models.CurrencyConversion:
    try:
        rate, converted = convert_currency(payload.amount, payload.base_currency, payload.quote_currency)
    except CurrencyServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    db_item = models.CurrencyConversion(
        amount=payload.amount,
        base_currency=payload.base_currency.upper(),
        quote_currency=payload.quote_currency.upper(),
        rate=rate,
        converted_amount=converted,
    )
    try:
        session.add(db_item)
        session.commit()
        session.refresh(db_item)
    except SQLAlchemyError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="database error") from exc
    return db_item


@app.post("/detect-currencies", response_model=CurrencyDetectionResponse)
def detect_currencies(
    payload: CurrencyDetectionRequest, 
    session: Session = Depends(get_db)
) -> CurrencyDetectionResponse:
    primary_currency = (payload.quote_currency or settings.primary_quote_currency).upper()
    target_currencies: list[str] = []
    for code in (primary_currency, settings.secondary_quote_currency):
        if not code:
            continue
        normalized = code.upper()
        if normalized not in target_currencies:
            target_currencies.append(normalized)
    for code in settings.additional_quote_currencies:
        if not code:
            continue
        normalized = code.upper()
        if normalized not in target_currencies:
            target_currencies.append(normalized)
    
    mentions = extract_currency_mentions(payload.text)
    items: list[DetectedCurrency] = []
    
    for mention in mentions:
        conversions: list[CurrencyConversionDetail] = []
        
     
        
        for quote_currency in valid_targets:
            try:
                rate, converted = convert_currency(mention.amount, mention.currency, quote_currency)
            except CurrencyServiceError:
                continue
            
          
            db_item = models.CurrencyConversion(
                amount=mention.amount,
                base_currency=mention.currency.upper(),
                quote_currency=quote_currency.upper(),
                rate=rate,
                converted_amount=converted,
            )
            try:
                session.add(db_item)
                session.commit()
            
            except SQLAlchemyError as exc:
                session.rollback()
          
                logger.error(f"Failed to save conversion to DB: {exc}")
            
            conversions.append(
                CurrencyConversionDetail(
                    quote_currency=quote_currency,
                    converted_amount=converted,
                    rate=rate,
                )
            )
        
        if not conversions:
            continue
        items.append(
            DetectedCurrency(
                source_amount=mention.amount,
                source_currency=mention.currency,
                conversions=conversions,
                match_text=mention.match_text,
                start_index=mention.start,
                end_index=mention.end,
            )
        )
    
    return CurrencyDetectionResponse(items=items)


@app.get("/history", response_model=HistoryResponse)
def read_history(limit: int = 10, session: Session = Depends(get_db)) -> HistoryResponse:
    limit = max(min(limit, 50), 1)
    try:
        
        conversions: List[models.CurrencyConversion] = (
            session.query(models.CurrencyConversion)
            .order_by(models.CurrencyConversion.created_at.desc())
            .limit(limit)
            .all()
        )
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="database error") from exc
    return HistoryResponse( conversions=conversions)
