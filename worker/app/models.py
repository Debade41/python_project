from sqlalchemy import Column, DateTime, Float, Integer, String, Text, func

from .db import Base




class CurrencyConversion(Base):
    __tablename__ = "currency_conversions"

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    base_currency = Column(String(8), nullable=False)
    quote_currency = Column(String(8), nullable=False)
    rate = Column(Float, nullable=False)
    converted_amount = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
