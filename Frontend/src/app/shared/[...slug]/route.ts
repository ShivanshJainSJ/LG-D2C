import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ slug: string[] }> }
) {
  const { slug } = await context.params;

  if (!slug || slug.length === 0 || slug.length > 2) {
    return renderQuotationUnavailableResponse();
  }

  const backendUrl = (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000")
    .trim()
    .replace(/\/+$/, "");

  let targetUrl: string;

  if (slug.length === 2) {
    // Pattern: /shared/{quotation_number}/{token}
    const [quotationNumber, token] = slug;
    if (
      !quotationNumber ||
      !quotationNumber.trim() ||
      !token ||
      token.trim().length < 8
    ) {
      return renderQuotationUnavailableResponse();
    }
    const cleanQuoteNum = encodeURIComponent(quotationNumber.trim());
    const cleanToken = encodeURIComponent(token.trim());
    targetUrl = `${backendUrl}/api/v1/public/quotations/${cleanQuoteNum}/${cleanToken}/pdf`;
  } else {
    // Pattern: /shared/{token}
    const [token] = slug;
    if (!token || token.trim().length < 8) {
      return renderQuotationUnavailableResponse();
    }
    const cleanToken = encodeURIComponent(token.trim());
    targetUrl = `${backendUrl}/api/v1/public/quotations/${cleanToken}/pdf`;
  }

  const forwardHeaders: Record<string, string> = {
    Accept: "application/pdf",
  };
  const userAgent = request.headers.get("user-agent");
  if (userAgent) forwardHeaders["User-Agent"] = userAgent;

  const forwardedFor =
    request.headers.get("x-forwarded-for") || request.headers.get("x-real-ip");
  if (forwardedFor) forwardHeaders["X-Forwarded-For"] = forwardedFor;

  try {
    const backendRes = await fetch(targetUrl, {
      method: "GET",
      headers: forwardHeaders,
      cache: "no-store",
    });

    if (!backendRes.ok) {
      if (backendRes.status === 404 || backendRes.status === 410) {
        return renderQuotationUnavailableResponse();
      }
      return new NextResponse(
        `Failed to retrieve quotation PDF (Status: ${backendRes.status})`,
        { status: backendRes.status }
      );
    }

    const contentDisposition =
      backendRes.headers.get("content-disposition") ||
      'attachment; filename="Livguard_Quotation.pdf"';
    const pdfBuffer = await backendRes.arrayBuffer();

    return new NextResponse(pdfBuffer, {
      status: 200,
      headers: {
        "Content-Type": "application/pdf",
        "Content-Disposition": contentDisposition,
        "Cache-Control": "no-store, no-cache, must-revalidate, private",
        Pragma: "no-cache",
        Expires: "0",
        "X-Content-Type-Options": "nosniff",
      },
    });
  } catch (error) {
    return new NextResponse("Error connecting to backend quotation service.", {
      status: 502,
    });
  }
}

function renderQuotationUnavailableResponse() {
  const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Livguard Quotation - Unavailable</title>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      margin: 0;
      background-color: #f8fafc;
      color: #0f172a;
      padding: 1.5rem;
      box-sizing: border-box;
    }
    .card {
      background: #ffffff;
      padding: 2.5rem 2rem;
      border-radius: 1rem;
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.05);
      border: 1px solid #e2e8f0;
      max-width: 440px;
      width: 100%;
      text-align: center;
    }
    .badge {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 3.5rem;
      height: 3.5rem;
      border-radius: 50%;
      background-color: #fef2f2;
      color: #dc2626;
      margin-bottom: 1.25rem;
    }
    .badge svg {
      width: 1.75rem;
      height: 1.75rem;
    }
    h1 {
      font-size: 1.25rem;
      font-weight: 700;
      color: #0f172a;
      margin: 0 0 0.75rem 0;
    }
    p {
      color: #64748b;
      font-size: 0.925rem;
      line-height: 1.5;
      margin: 0 0 1.5rem 0;
    }
    .brand-note {
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #94a3b8;
      border-top: 1px solid #f1f5f9;
      padding-top: 1.25rem;
      margin-top: 0.5rem;
    }
  </style>
</head>
<body>
  <div class="card">
    <div class="badge">
      <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
    </div>
    <h1>Quotation Unavailable</h1>
    <p>This quotation link is invalid, has expired, or has been revoked by the sales representative. Please request an updated link.</p>
    <div class="brand-note">Livguard Energy Unlimited</div>
  </div>
</body>
</html>`;

  return new NextResponse(html, {
    status: 404,
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      "Cache-Control": "no-store, no-cache, must-revalidate",
    },
  });
}
