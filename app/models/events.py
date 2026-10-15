"""Data models for SEC Material Events (Form 8-K), Insider Trading (Form 4), and Management Guidance."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class Form8KItemCode(str, Enum):
    ITEM_1_01 = "1.01"  # Entry into a Material Definitive Agreement
    ITEM_1_02 = "1.02"  # Termination of a Material Definitive Agreement
    ITEM_2_01 = "2.01"  # Completion of Acquisition or Disposition of Assets
    ITEM_2_02 = "2.02"  # Results of Operations and Financial Condition
    ITEM_2_03 = "2.03"  # Creation of a Direct Financial Obligation
    ITEM_2_05 = "2.05"  # Costs Associated with Exit or Disposal Activities
    ITEM_5_02 = "5.02"  # Departure of Directors or Principal Officers; Election/Appointment
    ITEM_7_01 = "7.01"  # Regulation FD Disclosure
    ITEM_8_01 = "8.01"  # Other Events


FORM_8K_ITEM_TITLES = {
    "1.01": "Entry into a Material Definitive Agreement",
    "1.02": "Termination of a Material Definitive Agreement",
    "2.01": "Acquisition or Disposition of Assets",
    "2.02": "Results of Operations and Financial Condition (Earnings)",
    "2.03": "Creation of a Direct Financial Obligation",
    "2.05": "Costs Associated with Exit / Restructuring",
    "5.02": "Departure/Election of Directors or Principal Officers",
    "7.01": "Regulation FD Disclosure",
    "8.01": "Other Material Corporate Events",
}


class MaterialEventItem(BaseModel):
    item_number: str
    item_name: str
    description: str | None = None


class MaterialEvent(BaseModel):
    event_id: str
    accession_number: str
    filing_date: str
    report_date: str
    form_type: str = "8-K"
    title: str
    items: list[MaterialEventItem] = Field(default_factory=list)
    summary: str
    source_url: str
    primary_doc: str | None = None


class InsiderTransactionCode(str, Enum):
    PURCHASE = "P"  # Open market or private purchase
    SALE = "S"      # Open market or private sale
    GRANT = "A"     # Grant, award, or other acquisition
    EXERCISE = "M"  # Exercise or conversion of derivative security
    GIFT = "G"      # Gift
    OTHER = "O"


class InsiderTransaction(BaseModel):
    transaction_id: str
    accession_number: str
    filing_date: str
    reporting_owner_name: str
    relationship_role: str  # e.g. "Chief Executive Officer", "Chief Financial Officer", "Director"
    transaction_date: str
    security_title: str = "Common Stock"
    transaction_code: str  # "P", "S", "A", "M"
    transaction_type: str  # "Purchase", "Sale", "Grant", "Exercise"
    shares: float
    price_per_share: float
    total_value: float
    is_acquisition: bool = True
    direct_or_indirect: str = "D"
    source_url: str


class TranscriptQuote(BaseModel):
    quote_id: str
    speaker: str
    title: str
    topic: str
    quote_text: str
    call_period: str
    source_url: str | None = None


class ManagementGuidance(BaseModel):
    guidance_id: str
    metric: str
    guidance_range: str
    period: str
    speaker: str
    source_url: str | None = None
