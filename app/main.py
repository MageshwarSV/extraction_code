from fastapi import FastAPI, UploadFile, File, Form
import os
from pathlib import Path
from engine.extractor import run_extraction
from dotenv import load_dotenv
import json
from typing import List, Dict, Any, Optional

# Optional DB helpers
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except Exception:
    psycopg2 = None
    RealDictCursor = None

# Load .env file from project root
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

app = FastAPI()

# /extract → returns raw_data + final_data
@app.post("/extract")
async def extract_invoice(
    client_id: int ,
    format_id: int ,
    file: UploadFile = File(...)
):
    os.makedirs("uploads", exist_ok=True)

    pdf_path = os.path.join("uploads", file.filename)
    with open(pdf_path, "wb") as f:
        f.write(await file.read())

    result = run_extraction(pdf_path, client_id, format_id)
    return result


def _db_connect():
    """Connect to Postgres using environment variables. Returns a connection or None."""
    if not psycopg2:
        return None
    dbname = os.getenv("DB_NAME") or os.getenv("POSTGRES_DB") or os.getenv("PGDATABASE")
    user = os.getenv("DB_USER") or os.getenv("POSTGRES_USER") or os.getenv("PGUSER")
    password = os.getenv("DB_PASSWORD") or os.getenv("POSTGRES_PASSWORD") or os.getenv("PGPASSWORD")
    host = os.getenv("DB_HOST") or os.getenv("POSTGRES_HOST") or os.getenv("PGHOST") or "localhost"
    port = int(os.getenv("DB_PORT") or os.getenv("POSTGRES_PORT") or 5432)
    try:
        conn = psycopg2.connect(dbname=dbname, user=user, password=password, host=host, port=port)
        return conn
    except Exception:
        return None


@app.get("/api/duplicates/count")
def get_duplicate_count():
    """Return count of rows in `doc_processing_log` with erp_entry_status = 'Duplicate' (case-insensitive)."""
    conn = _db_connect()
    if not conn:
        return {"ok": False, "error": "DB client not available or connection failed"}
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT COUNT(*) AS cnt FROM doc_processing_log WHERE UPPER(erp_entry_status) = 'DUPLICATE';")
            row = cur.fetchone()
            return {"ok": True, "duplicate_count": int(row['cnt'] or 0)}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        try:
            conn.close()
        except Exception:
            pass


@app.get("/api/duplicates/recent")
def get_recent_duplicates(limit: int = 20):
    """Return recent uploads from `doc_processing_log` with ERP status and duplicate flag."""
    conn = _db_connect()
    if not conn:
        return {"ok": False, "error": "DB client not available or connection failed"}
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT doc_id, doc_file_name, uploaded_on, erp_entry_status, overall_status
                FROM doc_processing_log
                ORDER BY uploaded_on DESC
                LIMIT %s
                """,
                (limit,)
            )
            rows = cur.fetchall() or []
            out: List[Dict[str, Any]] = []
            for r in rows:
                status = (r.get('erp_entry_status') or '').strip()
                is_dup = status.upper() == 'DUPLICATE'
                out.append({
                    'doc_id': r.get('doc_id'),
                    'filename': r.get('doc_file_name'),
                    'uploaded_on': r.get('uploaded_on').isoformat() if r.get('uploaded_on') else None,
                    'erp_entry_status': status,
                    'overall_status': r.get('overall_status'),
                    'is_duplicate': is_dup
                })
            return {"ok": True, "items": out}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        try:
            conn.close()
        except Exception:
            pass


