"""
Excel service — handles file upload, parsing, type detection, and dynamic SQL table creation.
"""

import pandas as pd
import os
import re
import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from ..config import get_settings
from ..database import DataSessionLocal
from ..models.dataset import Dataset
from ..core.exceptions import FileUploadError

settings = get_settings()


def _sanitize_table_name(filename: str) -> str:
    """Generate a safe SQL table name from a filename."""
    name = os.path.splitext(filename)[0]
    name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    name = re.sub(r'_+', '_', name).strip('_').lower()
    if not name or name[0].isdigit():
        name = f"tbl_{name}"
    # Add short unique suffix to avoid collisions
    short_id = uuid.uuid4().hex[:6]
    return f"{name}_{short_id}"


def _sanitize_column_name(col: str) -> str:
    """Sanitize a column name for SQL compatibility."""
    col = re.sub(r'[^a-zA-Z0-9_]', '_', str(col))
    col = re.sub(r'_+', '_', col).strip('_').lower()
    if not col or col[0].isdigit():
        col = f"col_{col}"
    return col


def _map_dtype_to_sql(dtype) -> str:
    """Map pandas dtype to SQLite-compatible type string."""
    dtype_str = str(dtype)
    if 'int' in dtype_str:
        return 'INTEGER'
    elif 'float' in dtype_str:
        return 'REAL'
    elif 'bool' in dtype_str:
        return 'INTEGER'  # SQLite stores booleans as int
    elif 'datetime' in dtype_str:
        return 'TEXT'  # SQLite stores dates as text
    else:
        return 'TEXT'


def _get_column_info(df: pd.DataFrame) -> list:
    """Extract column metadata from a DataFrame."""
    columns_info = []
    for col in df.columns:
        clean_name = _sanitize_column_name(col)
        dtype = df[col].dtype
        sql_type = _map_dtype_to_sql(dtype)
        non_null = int(df[col].notna().sum())
        unique_count = int(df[col].nunique())

        # Get sample values (up to 5 unique non-null values)
        samples = df[col].dropna().unique()[:5].tolist()
        samples = [str(s) for s in samples]

        columns_info.append({
            "original_name": str(col),
            "clean_name": clean_name,
            "data_type": sql_type,
            "pandas_dtype": str(dtype),
            "non_null_count": non_null,
            "null_count": int(df[col].isna().sum()),
            "unique_count": unique_count,
            "sample_values": samples,
        })
    return columns_info


def _read_csv(file_path: str) -> pd.DataFrame:
    """Read a CSV, tolerating common encodings and delimiters."""
    last_error = None
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            # sep=None lets pandas sniff , ; \t | separators
            return pd.read_csv(file_path, encoding=encoding, sep=None, engine="python")
        except Exception as e:
            last_error = e
    raise FileUploadError(f"Failed to read CSV file: {last_error}")


def _read_tabular_file(file_path: str, original_filename: str, sheet_name: Optional[str]) -> pd.DataFrame:
    """Read an .xlsx/.xls/.csv file into a DataFrame."""
    ext = os.path.splitext(original_filename)[1].lower()

    if ext == ".csv":
        return _read_csv(file_path)

    try:
        if sheet_name:
            return pd.read_excel(file_path, sheet_name=sheet_name)
        return pd.read_excel(file_path)
    except Exception as e:
        raise FileUploadError(f"Failed to read Excel file: {e}")


async def parse_and_upload_excel(
    file_path: str,
    original_filename: str,
    db: AsyncSession,
    sheet_name: Optional[str] = None,
    dataset_name: Optional[str] = None,
) -> Dataset:
    """
    Parse an Excel or CSV file, create a SQL table, and insert the data.
    Returns the created Dataset metadata record.
    """
    df = _read_tabular_file(file_path, original_filename, sheet_name)

    if df.empty:
        raise FileUploadError("The uploaded file is empty")

    if len(df.columns) == 0:
        raise FileUploadError("No columns detected in the file")

    # Sanitize column names
    clean_columns = {}
    for col in df.columns:
        clean_columns[col] = _sanitize_column_name(col)
    df.rename(columns=clean_columns, inplace=True)

    # Handle duplicate column names
    seen = {}
    new_cols = []
    for col in df.columns:
        if col in seen:
            seen[col] += 1
            new_cols.append(f"{col}_{seen[col]}")
        else:
            seen[col] = 0
            new_cols.append(col)
    df.columns = new_cols

    # Generate table name
    table_name = _sanitize_table_name(original_filename)

    # Get column metadata
    columns_info = _get_column_info(df)

    # Build CREATE TABLE SQL
    col_defs = []
    for info in columns_info:
        col_defs.append(f'"{info["clean_name"]}" {info["data_type"]}')
    create_sql = f'CREATE TABLE IF NOT EXISTS "{table_name}" ({", ".join(col_defs)})'

    # Insert into data database
    async with DataSessionLocal() as data_session:
        # Create table
        await data_session.execute(text(create_sql))
        await data_session.commit()

        # Insert data in batches
        batch_size = 500
        col_names = [info["clean_name"] for info in columns_info]
        placeholders = ", ".join([f":{c}" for c in col_names])
        insert_sql = f'INSERT INTO "{table_name}" ({", ".join([f"{c}" for c in col_names])}) VALUES ({placeholders})'

        # Replace NaN with None for SQL compatibility
        df = df.where(pd.notna(df), None)

        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i + batch_size]
            records = batch.to_dict(orient='records')
            for record in records:
                await data_session.execute(text(insert_sql), record)
            await data_session.commit()

    # Create dataset metadata record in app database
    file_size = os.path.getsize(file_path) if os.path.exists(file_path) else None
    display_name = dataset_name or os.path.splitext(original_filename)[0]

    dataset = Dataset(
        name=display_name,
        original_filename=original_filename,
        table_name=table_name,
        file_size_bytes=file_size,
        row_count=len(df),
        column_count=len(df.columns),
        columns_info=columns_info,
        sheet_name=sheet_name,
        upload_path=file_path,
    )
    db.add(dataset)
    await db.commit()
    await db.refresh(dataset)

    return dataset


async def get_excel_sheets(file_path: str) -> list:
    """Get sheet names from an Excel file."""
    try:
        xls = pd.ExcelFile(file_path)
        return xls.sheet_names
    except Exception as e:
        raise FileUploadError(f"Failed to read Excel file: {str(e)}")


async def get_dataset_by_id(dataset_id: int, db: AsyncSession) -> Optional[Dataset]:
    """Get a dataset by ID."""
    from sqlalchemy import select
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    return result.scalar_one_or_none()


async def get_all_datasets(db: AsyncSession) -> list:
    """Get all datasets, newest first."""
    from sqlalchemy import select
    result = await db.execute(select(Dataset).order_by(Dataset.created_at.desc()))
    return result.scalars().all()


async def delete_dataset(dataset_id: int, db: AsyncSession) -> bool:
    """Delete a dataset and its associated SQL table."""
    dataset = await get_dataset_by_id(dataset_id, db)
    if not dataset:
        return False

    # Drop the data table
    async with DataSessionLocal() as data_session:
        await data_session.execute(text(f'DROP TABLE IF EXISTS "{dataset.table_name}"'))
        await data_session.commit()

    # Delete the uploaded file
    if dataset.upload_path and os.path.exists(dataset.upload_path):
        os.remove(dataset.upload_path)

    # Delete the metadata record
    await db.delete(dataset)
    await db.commit()
    return True
