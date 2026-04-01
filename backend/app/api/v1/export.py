from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import Optional
from datetime import date
import io
from app.core.deps import CurrentUser
from app.core.database import get_supabase_admin
from app.services.export_excel import generate_report_excel
from app.services.export_pdf import generate_report_pdf

router = APIRouter(prefix="/export", tags=["Export"])
db = get_supabase_admin()


@router.get("/excel")
def export_excel(
    current_user: CurrentUser,
    report_id: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    department_id: Optional[str] = None,
):
    """Hisobotni Excel formatida yuklab olish"""
    excel_bytes = generate_report_excel(
        report_id=report_id,
        date_from=date_from,
        date_to=date_to,
        department_id=department_id,
    )

    filename = f"hisobot_{date.today().isoformat()}.xlsx"
    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/pdf")
def export_pdf(
    current_user: CurrentUser,
    report_id: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    department_id: Optional[str] = None,
):
    """Hisobotni PDF formatida yuklab olish"""
    pdf_bytes = generate_report_pdf(
        report_id=report_id,
        date_from=date_from,
        date_to=date_to,
        department_id=department_id,
    )

    filename = f"hisobot_{date.today().isoformat()}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
