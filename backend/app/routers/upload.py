"""
Upload router — Excel file upload, dataset listing, preview, and deletion.
(No authentication — open access)
"""

import os
import traceback
import uuid
import aiofiles
from fastapi import APIRouter, Depends, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List

from ..database import get_app_db, get_table_sample, get_table_row_count
from ..services import excel_service
from ..core.exceptions import AppException, NotFoundError, FileUploadError
from ..config import get_settings

settings = get_settings()

router = APIRouter(prefix="/api/upload", tags=["Data Upload"])


# ============================================
# Response Schemas
# ============================================

class ColumnInfo(BaseModel):
    original_name: str
    clean_name: str
    data_type: str
    non_null_count: int
    null_count: int
    unique_count: int
    sample_values: list


class DatasetResponse(BaseModel):
    id: int
    name: str
    original_filename: str
    table_name: str
    description: Optional[str]
    file_size_bytes: Optional[int]
    row_count: int
    column_count: int
    columns_info: Optional[list]
    created_at: str

    class Config:
        from_attributes = True


class DatasetListResponse(BaseModel):
    datasets: list
    total: int


class DataPreviewResponse(BaseModel):
    columns: list
    rows: list
    total_rows: int


ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".csv"}


# ============================================
# Endpoints
# ============================================

@router.post("/excel", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
async def upload_excel(
    file: UploadFile = File(...),
    dataset_name: Optional[str] = Form(None),
    sheet_name: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_app_db),
):
    """Upload an Excel (.xlsx/.xls) or CSV file and create a SQL table from it."""
    # Validate file extension
    _, ext = os.path.splitext(file.filename)
    if ext.lower() not in ALLOWED_EXTENSIONS:
        raise FileUploadError(
            f"Invalid file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Validate file size
    contents = await file.read()
    size_mb = len(contents) / (1024 * 1024)
    if size_mb > settings.MAX_UPLOAD_SIZE_MB:
        raise FileUploadError(
            f"File too large ({size_mb:.1f}MB). Maximum: {settings.MAX_UPLOAD_SIZE_MB}MB"
        )

    # Save file to disk
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    unique_name = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_name)

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(contents)

    # Parse and create SQL table
    try:
        dataset = await excel_service.parse_and_upload_excel(
            file_path=file_path,
            original_filename=file.filename,
            db=db,
            sheet_name=sheet_name or None,
            dataset_name=dataset_name,
        )
    except AppException:
        # Already a structured error with a useful message — clean up and re-raise as is
        if os.path.exists(file_path):
            os.remove(file_path)
        raise
    except Exception as e:
        # Clean up file on failure, and log the traceback so the cause is diagnosable
        if os.path.exists(file_path):
            os.remove(file_path)
        traceback.print_exc()
        raise FileUploadError(f"Failed to process file: {type(e).__name__}: {e}")

    return DatasetResponse(
        id=dataset.id,
        name=dataset.name,
        original_filename=dataset.original_filename,
        table_name=dataset.table_name,
        description=dataset.description,
        file_size_bytes=dataset.file_size_bytes,
        row_count=dataset.row_count,
        column_count=dataset.column_count,
        columns_info=dataset.columns_info,
        created_at=str(dataset.created_at),
    )


@router.get("/datasets", response_model=DatasetListResponse)
async def list_datasets(
    db: AsyncSession = Depends(get_app_db),
):
    """List all uploaded datasets."""
    from sqlalchemy import select
    from ..models.dataset import Dataset

    result = await db.execute(select(Dataset).order_by(Dataset.created_at.desc()))
    datasets = result.scalars().all()
    items = [
        {
            "id": d.id,
            "name": d.name,
            "original_filename": d.original_filename,
            "table_name": d.table_name,
            "row_count": d.row_count,
            "column_count": d.column_count,
            "file_size_bytes": d.file_size_bytes,
            "created_at": str(d.created_at),
        }
        for d in datasets
    ]
    return DatasetListResponse(datasets=items, total=len(items))


@router.get("/datasets/{dataset_id}/preview", response_model=DataPreviewResponse)
async def preview_dataset(
    dataset_id: int,
    limit: int = 20,
    db: AsyncSession = Depends(get_app_db),
):
    """Preview rows from a dataset's SQL table."""
    dataset = await excel_service.get_dataset_by_id(dataset_id, db)
    if not dataset:
        raise NotFoundError("Dataset")

    sample = await get_table_sample(dataset.table_name, limit=limit)
    total = await get_table_row_count(dataset.table_name)

    return DataPreviewResponse(
        columns=sample["columns"],
        rows=sample["rows"],
        total_rows=total,
    )


@router.delete("/datasets/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dataset(
    dataset_id: int,
    db: AsyncSession = Depends(get_app_db),
):
    """Delete a dataset and its SQL table."""
    dataset = await excel_service.get_dataset_by_id(dataset_id, db)
    if not dataset:
        raise NotFoundError("Dataset")

    await excel_service.delete_dataset(dataset_id, db)
