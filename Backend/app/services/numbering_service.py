from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.quotation import NumberSequence
from app.models.settings import CompanySettings, NumberingPolicy

class NumberingService:
    @staticmethod
    def _get_year_key(policy: NumberingPolicy, year_boundary_month: int = 4) -> str:
        now = datetime.now(timezone.utc)
        year = now.year
        month = now.month

        if policy == NumberingPolicy.CALENDAR_YEAR:
            return f"{year % 100:02d}" # "26" for 2026
        elif policy == NumberingPolicy.FINANCIAL_YEAR:
            if month >= year_boundary_month:
                start_yr = year % 100
                end_yr = (year + 1) % 100
            else:
                start_yr = (year - 1) % 100
                end_yr = year % 100
            return f"{start_yr:02d}-{end_yr:02d}" # "26-27"
        else:
            return "GLOBAL"

    @staticmethod
    def generate_quotation_number(db: Session) -> str:
        """
        Atomically generates the next unique quotation number using row-level locking.
        Never counts existing rows or allows duplicate sequence values.
        """
        company_setting = db.query(CompanySettings).order_by(CompanySettings.version.desc()).first()
        policy = company_setting.numbering_policy if company_setting else NumberingPolicy.CALENDAR_YEAR
        boundary_month = company_setting.year_boundary_month if company_setting else 4

        year_key = NumberingService._get_year_key(policy, boundary_month)
        
        # Lock and increment sequence
        seq_record = db.query(NumberSequence).filter(
            NumberSequence.sequence_type == "QUOTATION",
            NumberSequence.year_key == year_key
        ).with_for_update().first()

        if not seq_record:
            seq_record = NumberSequence(
                sequence_type="QUOTATION",
                year_key=year_key,
                current_seq=1
            )
            db.add(seq_record)
            db.flush()
            next_num = 1
        else:
            seq_record.current_seq += 1
            next_num = seq_record.current_seq
            db.flush()

        if policy == NumberingPolicy.CALENDAR_YEAR:
            return f"LG/{year_key}/{next_num:04d}"
        elif policy == NumberingPolicy.FINANCIAL_YEAR:
            return f"LG/{year_key}/{next_num:04d}"
        else:
            return f"LG/{next_num:06d}"

    @staticmethod
    def generate_order_number(db: Session) -> str:
        """
        Atomically generates the next unique order number.
        """
        company_setting = db.query(CompanySettings).order_by(CompanySettings.version.desc()).first()
        policy = company_setting.numbering_policy if company_setting else NumberingPolicy.CALENDAR_YEAR
        boundary_month = company_setting.year_boundary_month if company_setting else 4

        year_key = NumberingService._get_year_key(policy, boundary_month)

        seq_record = db.query(NumberSequence).filter(
            NumberSequence.sequence_type == "ORDER",
            NumberSequence.year_key == year_key
        ).with_for_update().first()

        if not seq_record:
            seq_record = NumberSequence(
                sequence_type="ORDER",
                year_key=year_key,
                current_seq=1
            )
            db.add(seq_record)
            db.flush()
            next_num = 1
        else:
            seq_record.current_seq += 1
            next_num = seq_record.current_seq
            db.flush()

        if policy == NumberingPolicy.CALENDAR_YEAR:
            return f"ORD/{year_key}/{next_num:04d}"
        elif policy == NumberingPolicy.FINANCIAL_YEAR:
            return f"ORD/{year_key}/{next_num:04d}"
        else:
            return f"ORD/{next_num:06d}"
