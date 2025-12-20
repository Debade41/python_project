from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, Field


class AnalysisRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)


class AnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    word_count: int
    char_count: int
    sentiment: str
    sentiment_score: float
    created_at: datetime


class ConversionRequest(BaseModel):
    amount: float = Field(..., gt=0)  # Оставляем как float
    base_currency: str = Field(..., min_length=3, max_length=4)
    quote_currency: str = Field(..., min_length=3, max_length=4)
class ConversionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    amount: float
    base_currency: str
    quote_currency: str
    rate: float
    converted_amount: float
    created_at: datetime


class HistoryResponse(BaseModel):
    analyses: List[AnalysisResponse]
    conversions: List[ConversionResponse]


class CurrencyDetectionRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=6000)
    quote_currency: str | None = Field(default=None, min_length=3, max_length=4)


class CurrencyConversionDetail(BaseModel):
    quote_currency: str
    converted_amount: float
    rate: float


class DetectedCurrency(BaseModel):
    source_amount: float
    source_currency: str
    conversions: List[CurrencyConversionDetail]
    match_text: str
    start_index: int
    end_index: int


class CurrencyDetectionResponse(BaseModel):
    items: List[DetectedCurrency]
