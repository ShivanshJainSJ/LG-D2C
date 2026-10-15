import asyncio
import traceback
from app.core.database import SessionLocal
from app.models.quotation import Quotation, QuotationRevision
from app.services.document_service import DocumentService
from app.models.settings import CompanySettings

async def main():
    db = SessionLocal()
    quotations = db.query(Quotation).all()
    print(f"Total quotations in DB: {len(quotations)}")
    for q in quotations:
        print(f"Quote ID: {q.id}, Number: {q.quotation_number}, Status: {q.status}")
        for r in q.revisions:
            print(f"  Revision ID: {r.id}, label: {r.revision_label}")
            try:
                cs = db.query(CompanySettings).order_by(CompanySettings.version.desc()).first()
                html = DocumentService.render_quotation_html(q, r, cs)
                print(f"  HTML render OK, length: {len(html)}")
                pdf = await DocumentService.generate_pdf_from_html(html)
                print(f"  PDF generate OK, length: {len(pdf)}")
                png = await DocumentService.generate_png_from_html(html)
                print(f"  PNG generate OK, length: {len(png)}")
            except Exception as e:
                print(f"  ERROR for quote {q.id} rev {r.id}: {e}")
                traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
