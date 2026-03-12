"""
Agent 2 — Data Ingestion Agent
Parses CSV / JSON uploads, normalises transactions, writes to PostgreSQL.
"""

import io
import json
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Transaction

logger = logging.getLogger("agent.ingestion")

REQUIRED_COLUMNS = {"date", "description", "amount"}
CATEGORY_MAP = {
    "salary": "revenue",
    "invoice": "revenue",
    "payment": "expense",
    "rent": "expense",
    "utilities": "expense",
    "software": "expense",
    "travel": "expense",
    "marketing": "expense",
    "refund": "revenue",
}


def _infer_category(description: str) -> str:
    desc_lower = description.lower()
    for keyword, cat in CATEGORY_MAP.items():
        if keyword in desc_lower:
            return cat
    return "other"


def parse_csv(content: bytes) -> pd.DataFrame:
    df = pd.read_csv(io.BytesIO(content))
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing required columns: {missing}")

    df["date"] = pd.to_datetime(df["date"], infer_datetime_format=True, utc=False)
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    df["description"] = df["description"].fillna("").astype(str).str.strip()

    if "category" not in df.columns:
        df["category"] = df["description"].apply(_infer_category)

    if "currency" not in df.columns:
        df["currency"] = "USD"

    return df


def parse_json(content: bytes) -> pd.DataFrame:
    records = json.loads(content)
    if isinstance(records, dict) and "transactions" in records:
        records = records["transactions"]
    df = pd.DataFrame(records)
    # reuse CSV normalisation logic
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    df["date"] = pd.to_datetime(df["date"], infer_datetime_format=True, utc=False)
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    if "category" not in df.columns:
        df["category"] = df["description"].apply(_infer_category)
    if "currency" not in df.columns:
        df["currency"] = "USD"
    return df


async def ingest(
    content: bytes,
    file_type: str,
    run_id: Optional[UUID],
    db: AsyncSession,
) -> dict:
    """
    Main entry point called by the LangGraph workflow node.
    Returns structured ingestion summary written to graph state.
    """
    logger.info("DataIngestionAgent: parsing %s file (%d bytes)", file_type, len(content))

    if file_type == "csv":
        df = parse_csv(content)
    elif file_type == "json":
        df = parse_json(content)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")

    records = []
    for _, row in df.iterrows():
        tx = Transaction(
            run_id=run_id,
            date=row["date"].to_pydatetime(),
            description=row["description"],
            category=row.get("category", "other"),
            amount=float(row["amount"]),
            currency=row.get("currency", "USD"),
        )
        db.add(tx)
        records.append(
            {
                "date": row["date"].isoformat(),
                "description": row["description"],
                "category": row.get("category", "other"),
                "amount": float(row["amount"]),
                "currency": row.get("currency", "USD"),
            }
        )

    await db.commit()
    logger.info("DataIngestionAgent: committed %d transactions", len(records))

    return {
        "total_transactions": len(records),
        "date_range": {
            "start": df["date"].min().isoformat(),
            "end": df["date"].max().isoformat(),
        },
        "categories": df["category"].value_counts().to_dict(),
        "transactions": records,
    }
