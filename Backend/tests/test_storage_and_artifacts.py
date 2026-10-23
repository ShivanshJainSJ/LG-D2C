import pytest
import os
import shutil
import hashlib
from decimal import Decimal
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.product import Product
from app.models.quotation import Quotation, QuotationRevision, QuotationItem, QuotationStatus
from app.models.sharing import QuotationArtifact, QuotationShareLink, SharedQuotationAccessLog
from app.services.storage_service import LocalStorageProvider, S3StorageProvider
from app.services.quotation_artifact_service import QuotationArtifactService
from app.services.document_service import DocumentService

TEST_STORAGE_DIR = "./uploads/test_private_artifacts"

@pytest.fixture
def local_storage():
    os.makedirs(TEST_STORAGE_DIR, exist_ok=True)
    provider = LocalStorageProvider(TEST_STORAGE_DIR)
    yield provider
    if os.path.exists(TEST_STORAGE_DIR):
        shutil.rmtree(TEST_STORAGE_DIR, ignore_errors=True)

@pytest.mark.anyio
async def test_local_storage_upload_and_retrieval(local_storage: LocalStorageProvider):
    test_key = "test/doc_1.pdf"
    test_data = b"%PDF-1.4 sample PDF binary data"
    
    # 1. Upload
    key = await local_storage.upload(test_key, test_data, content_type="application/pdf")
    assert key == test_key
    assert await local_storage.exists(test_key) is True

    # 2. Retrieve
    retrieved = await local_storage.get(test_key)
    assert retrieved == test_data

    # 3. Delete
    deleted = await local_storage.delete(test_key)
    assert deleted is True
    assert await local_storage.exists(test_key) is False

@pytest.mark.anyio
async def test_local_storage_traversal_prevention(local_storage: LocalStorageProvider):
    with pytest.raises(ValueError, match="Directory traversal"):
        await local_storage.upload("../../outside.pdf", b"malicious")

    with pytest.raises(ValueError, match="Directory traversal"):
        await local_storage.get("../outside.pdf")

@pytest.mark.anyio
async def test_local_storage_missing_file_raises_not_found(local_storage: LocalStorageProvider):
    with pytest.raises(FileNotFoundError, match="not found"):
        await local_storage.get("nonexistent/missing.pdf")

@pytest.mark.anyio
async def test_s3_storage_mocked_operations():
    mock_boto_client = MagicMock()
    mock_boto_client.get_object.return_value = {
        "Body": MagicMock(read=MagicMock(return_value=b"%PDF-1.4 from S3"))
    }
    mock_boto_client.head_object.return_value = {"ContentLength": 100}

    with patch("app.services.storage_service.S3StorageProvider._get_client", return_value=mock_boto_client):
        s3_provider = S3StorageProvider(
            account_id="acc123",
            access_key_id="key123",
            secret_access_key="sec123",
            bucket_name="my-bucket"
        )

        # Upload
        key = await s3_provider.upload("quotations/q1/rev0.pdf", b"%PDF-1.4 test")
        assert key == "quotations/q1/rev0.pdf"
        mock_boto_client.put_object.assert_called_once()

        # Get
        data = await s3_provider.get("quotations/q1/rev0.pdf")
        assert data == b"%PDF-1.4 from S3"

        # Exists
        exists = await s3_provider.exists("quotations/q1/rev0.pdf")
        assert exists is True

        # Delete
        deleted = await s3_provider.delete("quotations/q1/rev0.pdf")
        assert deleted is True
        mock_boto_client.delete_object.assert_called_once()

def create_sample_quotation_and_revision(db_session: Session) -> tuple[Quotation, QuotationRevision]:
    agent = db_session.query(User).filter(User.role == UserRole.AGENT).first()
    product = db_session.query(Product).first()

    quote = Quotation(
        quotation_number="LQ-2026-TEST01",
        current_revision_number=0,
        agent_id=agent.id,
        customer_name="Ramesh Sharma",
        customer_mobile="+919876543210",
        customer_email="ramesh@example.com",
        customer_address="123 Test Street, Delhi",
        status=QuotationStatus.ISSUED
    )
    db_session.add(quote)
    db_session.flush()

    rev = QuotationRevision(
        quotation_id=quote.id,
        revision_number=0,
        revision_label="Original",
        subtotal=product.base_price,
        discount_amount=Decimal("0.00"),
        coupon_code=None,
        tax_rate=Decimal("18.00"),
        tax_amount=product.base_price * Decimal("0.18"),
        grand_total=product.base_price * Decimal("1.18"),
        company_snapshot='{"company_name": "Livguard Energy", "phone": "1800-102-5551", "terms": "15 days"}',
        tax_snapshot='{"rate": 18.0, "policy": "GST Standard"}',
        is_superseded=False,
        created_by_id=agent.id
    )
    db_session.add(rev)
    db_session.flush()

    item = QuotationItem(
        revision_id=rev.id,
        product_id=product.id,
        sku=product.sku,
        product_name=product.name,
        description=product.description,
        unit_price=product.base_price,
        quantity=1,
        total_price=product.base_price
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(quote)
    db_session.refresh(rev)
    return quote, rev

@pytest.mark.anyio
async def test_artifact_creation_checksum_and_size(db_session: Session, local_storage: LocalStorageProvider):
    quote, rev = create_sample_quotation_and_revision(db_session)

    # First call: creates and persists immutable artifact
    artifact, pdf_bytes, is_new = await QuotationArtifactService.get_or_create_artifact(
        db=db_session,
        quotation=quote,
        revision=rev,
        storage=local_storage
    )

    assert is_new is True
    assert artifact is not None
    assert artifact.revision_id == rev.id
    assert artifact.quotation_id == quote.id
    assert artifact.byte_size == len(pdf_bytes)
    assert artifact.sha256_hash == hashlib.sha256(pdf_bytes).hexdigest()
    assert artifact.content_type == "application/pdf"
    assert await local_storage.exists(artifact.storage_key) is True

    # Database verification
    db_art = db_session.query(QuotationArtifact).filter(QuotationArtifact.revision_id == rev.id).first()
    assert db_art is not None
    assert db_art.id == artifact.id
    assert db_art.sha256_hash == artifact.sha256_hash

@pytest.mark.anyio
async def test_artifact_idempotent_reuse_without_regeneration(db_session: Session, local_storage: LocalStorageProvider):
    quote, rev = create_sample_quotation_and_revision(db_session)

    # 1. Create artifact
    art1, bytes1, is_new1 = await QuotationArtifactService.get_or_create_artifact(
        db=db_session, quotation=quote, revision=rev, storage=local_storage
    )
    assert is_new1 is True

    # 2. Second request for same revision: must reuse existing artifact without re-rendering PDF
    with patch("app.services.document_service.DocumentService.generate_pdf_from_html") as mock_generate:
        art2, bytes2, is_new2 = await QuotationArtifactService.get_or_create_artifact(
            db=db_session, quotation=quote, revision=rev, storage=local_storage
        )
        # Verify document service generator was NOT called because artifact was reused
        mock_generate.assert_not_called()

    assert is_new2 is False
    assert art2.id == art1.id
    assert bytes2 == bytes1
    assert art2.sha256_hash == art1.sha256_hash

@pytest.mark.anyio
async def test_separate_revisions_have_separate_artifacts(db_session: Session, local_storage: LocalStorageProvider):
    quote, rev0 = create_sample_quotation_and_revision(db_session)

    # Create revision 1
    agent = db_session.query(User).filter(User.role == UserRole.AGENT).first()
    product = db_session.query(Product).first()

    rev1 = QuotationRevision(
        quotation_id=quote.id,
        revision_number=1,
        revision_label="Revision 1",
        subtotal=product.base_price * 2,
        discount_amount=Decimal("0.00"),
        tax_rate=Decimal("18.00"),
        tax_amount=(product.base_price * 2) * Decimal("0.18"),
        grand_total=(product.base_price * 2) * Decimal("1.18"),
        is_superseded=False,
        created_by_id=agent.id
    )
    db_session.add(rev1)
    db_session.flush()

    item1 = QuotationItem(
        revision_id=rev1.id,
        product_id=product.id,
        sku=product.sku,
        product_name=product.name,
        unit_price=product.base_price,
        quantity=2,
        total_price=product.base_price * 2
    )
    db_session.add(item1)
    db_session.commit()

    # Generate artifact for Rev 0
    art0, bytes0, _ = await QuotationArtifactService.get_or_create_artifact(
        db=db_session, quotation=quote, revision=rev0, storage=local_storage
    )

    # Generate artifact for Rev 1
    art1, bytes1, _ = await QuotationArtifactService.get_or_create_artifact(
        db=db_session, quotation=quote, revision=rev1, storage=local_storage
    )

    # Assert distinct artifacts
    assert art0.id != art1.id
    assert art0.storage_key != art1.storage_key
    assert art0.revision_id == rev0.id
    assert art1.revision_id == rev1.id
    assert art0.byte_size != art1.byte_size or art0.sha256_hash != art1.sha256_hash

    # Verify Rev 0's stored bytes remain unmodified
    rev0_stored_bytes = await local_storage.get(art0.storage_key)
    assert rev0_stored_bytes == bytes0

@pytest.mark.anyio
async def test_storage_failure_does_not_falsely_save_artifact(db_session: Session):
    quote, rev = create_sample_quotation_and_revision(db_session)

    mock_failing_storage = MagicMock()
    mock_failing_storage.exists.return_value = False
    mock_failing_storage.upload.side_effect = IOError("Simulated cloud storage network timeout")

    with pytest.raises(IOError, match="Simulated cloud storage network timeout"):
        await QuotationArtifactService.get_or_create_artifact(
            db=db_session, quotation=quote, revision=rev, storage=mock_failing_storage
        )

    # Ensure no false artifact record was left in the database
    persisted = db_session.query(QuotationArtifact).filter(QuotationArtifact.revision_id == rev.id).first()
    assert persisted is None

@pytest.mark.anyio
async def test_database_failure_after_storage_upload_triggers_storage_cleanup(db_session: Session, local_storage: LocalStorageProvider):
    quote, rev = create_sample_quotation_and_revision(db_session)

    # Mock db.commit to simulate database constraint/connection crash
    with patch.object(db_session, "commit", side_effect=RuntimeError("Simulated database failure")):
        with pytest.raises(RuntimeError, match="Simulated database failure"):
            await QuotationArtifactService.get_or_create_artifact(
                db=db_session, quotation=quote, revision=rev, storage=local_storage
            )

    # Storage cleanup should have deleted the orphaned file
    expected_key = f"quotations/{quote.id}/revisions/{rev.id}_rev{rev.revision_number}.pdf"
    assert await local_storage.exists(expected_key) is False

    # And no DB artifact should exist
    persisted = db_session.query(QuotationArtifact).filter(QuotationArtifact.revision_id == rev.id).first()
    assert persisted is None

@pytest.mark.anyio
async def test_missing_snapshots_fallback_correctly(db_session: Session, local_storage: LocalStorageProvider):
    quote, rev = create_sample_quotation_and_revision(db_session)
    rev.company_snapshot = None
    rev.tax_snapshot = None
    db_session.commit()

    artifact, pdf_bytes, is_new = await QuotationArtifactService.get_or_create_artifact(
        db=db_session, quotation=quote, revision=rev, storage=local_storage
    )
    assert is_new is True
    assert artifact.byte_size > 0
    assert len(pdf_bytes) > 0

@pytest.mark.anyio
async def test_concurrent_integrity_race_handling(db_session: Session, local_storage: LocalStorageProvider):
    quote, rev = create_sample_quotation_and_revision(db_session)

    # Pre-create artifact
    art1, bytes1, _ = await QuotationArtifactService.get_or_create_artifact(
        db=db_session, quotation=quote, revision=rev, storage=local_storage
    )

    # Calling again returns existing committed record
    art2, bytes2, is_new = await QuotationArtifactService.get_or_create_artifact(
        db=db_session, quotation=quote, revision=rev, storage=local_storage
    )
    assert is_new is False
    assert art2.id == art1.id
    assert bytes2 == bytes1

def test_production_refuses_silent_local_storage_fallback():
    from app.core.config import settings
    from app.services.storage_service import get_storage_service

    orig_env = settings.ENVIRONMENT
    orig_backend = settings.STORAGE_BACKEND
    try:
        settings.ENVIRONMENT = "production"
        settings.STORAGE_BACKEND = "local"
        with pytest.raises(RuntimeError, match="Ephemeral local storage cannot be used in production"):
            get_storage_service()
    finally:
        settings.ENVIRONMENT = orig_env
        settings.STORAGE_BACKEND = orig_backend
