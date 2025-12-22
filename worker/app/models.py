from sqlalchemy import Column, DateTime, Float, Integer, String, Text, func

from .db import Base


class TextAnalysis(Base):
    __tablename__ = "text_analysis"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    word_count = Column(Integer, nullable=False)
    char_count = Column(Integer, nullable=False)
    sentiment = Column(String(32), nullable=False)
    sentiment_score = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class CurrencyConversion(Base):
    __tablename__ = "currency_conversions"

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    base_currency = Column(String(8), nullable=False)
    quote_currency = Column(String(8), nullable=False)
    rate = Column(Float, nullable=False)
    converted_amount = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
