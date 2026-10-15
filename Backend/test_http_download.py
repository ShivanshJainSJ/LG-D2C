import httpx
from app.core.database import SessionLocal
from app.models.user import User

db = SessionLocal()
aagam = db.query(User).filter(User.email == "aagam.agent@livguard.com").first()
print("Aagam found:", aagam.email)

# Generate a valid token for aagam
from app.core.security import create_access_token
token = create_access_token(aagam.id, aagam.role.value)
headers = {"Authorization": f"Bearer {token}"}

quote_id = "e30996c5-7f00-46f5-a69e-ce9709785148"
rev_id = "db9bda1a-a65a-4b09-8f23-b917af103598"

# 1. Test against FastAPI directly (port 8000)
try:
    pdf_res = httpx.get(f"http://127.0.0.1:8000/api/v1/agent/quotations/{quote_id}/revisions/{rev_id}/pdf", headers=headers, timeout=30.0)
    print("Port 8000 PDF status:", pdf_res.status_code, "Length:", len(pdf_res.content) if pdf_res.status_code == 200 else pdf_res.text)
except Exception as e:
    print("Port 8000 PDF Exception:", e)

# 2. Test against Next.js rewrite (port 3000)
try:
    pdf_res_3000 = httpx.get(f"http://127.0.0.1:3000/api/v1/agent/quotations/{quote_id}/revisions/{rev_id}/pdf", headers=headers, timeout=30.0)
    print("Port 3000 PDF status:", pdf_res_3000.status_code, "Length:", len(pdf_res_3000.content) if pdf_res_3000.status_code == 200 else pdf_res_3000.text)
except Exception as e:
    print("Port 3000 PDF Exception:", e)

# 3. Test PNG against port 3000
try:
    png_res_3000 = httpx.get(f"http://127.0.0.1:3000/api/v1/agent/quotations/{quote_id}/revisions/{rev_id}/png", headers=headers, timeout=30.0)
    print("Port 3000 PNG status:", png_res_3000.status_code, "Length:", len(png_res_3000.content) if png_res_3000.status_code == 200 else png_res_3000.text)
except Exception as e:
    print("Port 3000 PNG Exception:", e)
