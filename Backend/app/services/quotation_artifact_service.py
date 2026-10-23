import hashlib
import logging
from typing import Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.models.quotation import Quotation, QuotationRevision
from app.models.settings import CompanySettings
from app.models.sharing import QuotationArtifact
from app.services.document_service import DocumentService
from app.services.storage_service import get_storage_service, StorageProvider

logger = logging.getLogger(__name__)

class QuotationArtifactService:
    """
    Manages the lifecycle of immutable quotation revision PDF artifacts.
    An artifact is created once when first requested (e.g. upon first share or download)
    and remains permanently sealed and immutable thereafter.
    """

    @classmethod
    async def get_or_create_artifact(
        cls,
        db: Session,
        quotation: Quotation,
        revision: QuotationRevision,
        storage: StorageProvider = None
    ) -> Tuple[QuotationArtifact, bytes, bool]:
        """
        Retrieves the existing immutable artifact for a revision, or generates and
        persists a new one if none exists.
        
        Returns:
            Tuple[QuotationArtifact, bytes, bool]: (artifact_record, pdf_bytes, is_newly_created)
        """
        if storage is None:
            storage = get_storage_service()

        # 1. Check if artifact record already exists in database
        existing_artifact = db.query(QuotationArtifact).filter(
            QuotationArtifact.revision_id == revision.id
        ).first()

        if existing_artifact:
            try:
                # Retrieve existing immutable bytes from private storage
                pdf_bytes = await storage.get(existing_artifact.storage_key)
                return existing_artifact, pdf_bytes, False
            except FileNotFoundError:
                logger.warning(
                    f"Artifact record {existing_artifact.id} exists for revision {revision.id}, "
                    f"but file '{existing_artifact.storage_key}' was missing in storage. Regenerating."
                )
                # Fall through to regenerate missing physical artifact

        # 2. Render PDF using document generation service
        company_settings = db.query(CompanySettings).order_by(CompanySettings.version.desc()).first()
        html_content = DocumentService.render_quotation_html(quotation, revision, company_settings)
        pdf_bytes = await DocumentService.generate_pdf_from_html(html_content)

        if not pdf_bytes or len(pdf_bytes) == 0:
            raise RuntimeError("PDF generation failed: Output byte stream is empty.")

        # 3. Calculate cryptographic checksum and size
        sha256_hash = hashlib.sha256(pdf_bytes).hexdigest()
        byte_size = len(pdf_bytes)

        # 4. Storage key format: quotations/<quotation_id>/revisions/<revision_id>_<rev_num>.pdf
        storage_key = f"quotations/{quotation.id}/revisions/{revision.id}_rev{revision.revision_number}.pdf"

        # 5. Persist bytes to private storage
        storage_provider_name = "r2" if settings.STORAGE_BACKEND == "r2" else "local"
        await storage.upload(
            key=storage_key,
            data=pdf_bytes,
            content_type="application/pdf"
        )

        # 6. Insert artifact record with concurrency/idempotency protection
        if existing_artifact:
            # Update existing record if file was regenerated
            existing_artifact.storage_key = storage_key
            existing_artifact.byte_size = byte_size
            existing_artifact.sha256_hash = sha256_hash
            existing_artifact.storage_provider = storage_provider_name
            try:
                db.commit()
                db.refresh(existing_artifact)
                return existing_artifact, pdf_bytes, False
            except Exception:
                db.rollback()
                raise

        new_artifact = QuotationArtifact(
            quotation_id=quotation.id,
            revision_id=revision.id,
            storage_key=storage_key,
            storage_provider=storage_provider_name,
            content_type="application/pdf",
            byte_size=byte_size,
            sha256_hash=sha256_hash
        )
        db.add(new_artifact)

        try:
            db.commit()
            db.refresh(new_artifact)
            logger.info(
                f"Successfully created immutable artifact {new_artifact.id} for revision {revision.id} "
                f"(size={byte_size} bytes, sha256={sha256_hash[:12]}...)"
            )
            return new_artifact, pdf_bytes, True
        except IntegrityError:
            # Handle concurrent race condition: another request committed an artifact for this revision
            db.rollback()
            concurrent_artifact = db.query(QuotationArtifact).filter(
                QuotationArtifact.revision_id == revision.id
            ).first()
            if concurrent_artifact:
                concurrent_bytes = await storage.get(concurrent_artifact.storage_key)
                return concurrent_artifact, concurrent_bytes, False
            raise
        except Exception:
            db.rollback()
            try:
                await storage.delete(storage_key)
            except Exception:
                pass
            raise
