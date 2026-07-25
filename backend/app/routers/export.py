"""
Export router — export query results to CSV, Excel, or PDF.
(No authentication — open access)
"""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import io

from ..services import export_service

router = APIRouter(prefix="/api/export", tags=["Export"])


class ExportRequest(BaseModel):
    columns: List[str]
    rows: List[dict]
    title: Optional[str] = "Query Results"
    sql: Optional[str] = None
    format: str = "csv"  # csv, excel, pdf


@router.post("/download")
async def export_data(
    request: ExportRequest,
):
    """Export data in the requested format."""
    if request.format == "csv":
        content = export_service.export_to_csv(request.columns, request.rows)
        return StreamingResponse(
            io.BytesIO(content),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=export.csv"},
        )
    elif request.format == "excel":
        content = export_service.export_to_excel(request.columns, request.rows)
        return StreamingResponse(
            io.BytesIO(content),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=export.xlsx"},
        )
    elif request.format == "pdf":
        content = export_service.export_to_pdf(
            request.columns, request.rows, request.title, request.sql
        )
        return StreamingResponse(
            io.BytesIO(content),
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=export.pdf"},
        )
    else:
        return {"error": f"Unsupported format: {request.format}"}
