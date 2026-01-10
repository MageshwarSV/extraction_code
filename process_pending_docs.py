#!/usr/bin/env python3
"""
Process Pending Documents Worker (With Lock & 30-sec Schedule)
---------------------------------------------------------------
This script:
1. Runs every 30 seconds
2. Only runs if not already running (lock file mechanism)
3. Queries DB for logs where data_extraction_status = 'Not Started'
4. Sends each PDF to the extraction API (port 8000)
5. Stores response in extracted_json field
6. Updates data_extraction_status to 'Completed'
"""

import os
import sys
import json
import time
import fcntl
import logging
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

# ============================================
# Configuration
# ============================================
DB_CONFIG = {
    "dbname": "mydb",
    "user": "sql_developer",
    "password": "Dev@123",
    "host": "103.14.121.15",
    "port": 5432,
}

# Extraction API endpoint
EXTRACTION_API_URL = "http://103.14.121.15:8000/extract"

# PDF storage base path on server
PDF_BASE_PATH = "/root/boostentry_pdf"

# Lock file to prevent multiple instances
LOCK_FILE = "/tmp/wbai_worker.lock"

# Check interval (seconds)
CHECK_INTERVAL = 30

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ============================================
# Lock Mechanism - Prevent Duplicate Runs
# ============================================
class SingleInstanceLock:
    """Ensures only one instance of the script runs at a time"""
    
    def __init__(self, lock_file):
        self.lock_file = lock_file
        self.lock_handle = None
    
    def acquire(self):
        """Try to acquire lock. Returns True if successful, False if already running."""
        try:
            self.lock_handle = open(self.lock_file, 'w')
            fcntl.flock(self.lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            # Write PID to lock file
            self.lock_handle.write(str(os.getpid()))
            self.lock_handle.flush()
            return True
        except (IOError, OSError):
            # Another instance is running
            if self.lock_handle:
                self.lock_handle.close()
            return False
    
    def release(self):
        """Release the lock"""
        if self.lock_handle:
            try:
                fcntl.flock(self.lock_handle, fcntl.LOCK_UN)
                self.lock_handle.close()
                os.remove(self.lock_file)
            except:
                pass


# ============================================
# Database Functions
# ============================================
def get_db_connection():
    """Create database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return None


def get_pending_documents():
    """Get all documents with data_extraction_status = 'Not Started'"""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        query = """
            SELECT doc_id, doc_file_name, saved_path, client_id, doc_format_id
            FROM boostentryai.doc_processing_log
            WHERE data_extraction_status = 'Not Started'
            ORDER BY uploaded_on ASC
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return rows
    except Exception as e:
        logger.error(f"Failed to fetch pending documents: {e}")
        conn.close()
        return []


def update_document_status(doc_id, extracted_json, status="Completed", error_msg=None):
    """Update document status and extracted JSON in database"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        if status == "In Progress":
            # Set start time when processing begins
            query = """
                UPDATE boostentryai.doc_processing_log
                SET data_extraction_status = %s,
                    data_extraction_start_time = %s,
                    updated_at = %s
                WHERE doc_id = %s
            """
            cursor.execute(query, (status, datetime.now(), datetime.now(), doc_id))
        else:
            # Set end time when completed or failed
            query = """
                UPDATE boostentryai.doc_processing_log
                SET data_extraction_status = %s,
                    extracted_json = %s,
                    data_extraction_end_time = %s,
                    updated_at = %s
                WHERE doc_id = %s
            """
            cursor.execute(query, (status, json.dumps(extracted_json) if extracted_json else None,
                                   datetime.now(), datetime.now(), doc_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Updated doc_id={doc_id} to status={status}")
        return True
    except Exception as e:
        logger.error(f"Failed to update document {doc_id}: {e}")
        conn.close()
        return False


# ============================================
# Extraction API Function
# ============================================
def send_to_extraction_api(pdf_path, client_id=1, format_id=1):
    """Send PDF to extraction API and get response"""
    
    # Check if file exists
    if not os.path.exists(pdf_path):
        logger.error(f"PDF file not found: {pdf_path}")
        return None, f"File not found: {pdf_path}"
    
    try:
        # Open and send file to API
        with open(pdf_path, 'rb') as pdf_file:
            files = {'file': (os.path.basename(pdf_path), pdf_file, 'application/pdf')}
            params = {'client_id': client_id, 'format_id': format_id}
            
            full_url = f"{EXTRACTION_API_URL}?client_id={client_id}&format_id={format_id}"
            logger.info(f"Sending to API: {full_url}")
            response = requests.post(
                EXTRACTION_API_URL,
                files=files,
                params=params,
                timeout=None  # No timeout - wait until response is received
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Extraction successful for: {pdf_path}")
                return result, None
            else:
                error_msg = f"API error {response.status_code}: {response.text}"
                logger.error(error_msg)
                return None, error_msg
                
    except requests.exceptions.Timeout:
        error_msg = "API request timed out after 5 minutes"
        logger.error(error_msg)
        return None, error_msg
    except Exception as e:
        error_msg = f"API request failed: {str(e)}"
        logger.error(error_msg)
        return None, error_msg


# ============================================
# Process Pending Documents
# ============================================
def process_pending():
    """Process all currently pending documents"""
    
    pending_docs = get_pending_documents()
    
    if not pending_docs:
        logger.info("No pending documents found.")
        return 0, 0
    
    logger.info(f"Found {len(pending_docs)} pending document(s)")
    
    success_count = 0
    fail_count = 0
    
    for doc in pending_docs:
        doc_id = doc['doc_id']
        file_name = doc.get('doc_file_name', '')
        saved_path = doc.get('saved_path', '')
        client_id = doc.get('client_id', 1) or 1
        format_id = doc.get('doc_format_id', 1) or 1
        
        # Construct full PDF path
        pdf_path = None
        
        # Try 1: Use saved_path if it's an absolute path
        if saved_path and os.path.isabs(saved_path) and os.path.exists(saved_path):
            pdf_path = saved_path
        
        # Try 2: Use file_name directly
        if not pdf_path:
            direct_path = os.path.join(PDF_BASE_PATH, file_name)
            if os.path.exists(direct_path):
                pdf_path = direct_path
        
        # Try 3: If filename has '_Invoice_', try without it
        if not pdf_path and '_Invoice_' in file_name:
            alt_name = file_name.replace('_Invoice_', '_')
            alt_path = os.path.join(PDF_BASE_PATH, alt_name)
            if os.path.exists(alt_path):
                pdf_path = alt_path
                logger.info(f"Found file with alternate name: {alt_name}")
        
        # Try 4: Search for matching file by date pattern
        if not pdf_path:
            # Extract date part from filename (e.g., 20260109_130312)
            import re
            date_match = re.search(r'(\d{8}_\d{6})', file_name)
            if date_match:
                date_pattern = date_match.group(1)
                # Search for files matching this date pattern
                for f in os.listdir(PDF_BASE_PATH):
                    if date_pattern in f and f.endswith('.pdf'):
                        pdf_path = os.path.join(PDF_BASE_PATH, f)
                        logger.info(f"Found file by date pattern: {f}")
                        break
        
        # If still not found, use original path for error message
        if not pdf_path:
            pdf_path = os.path.join(PDF_BASE_PATH, file_name)
        
        logger.info(f"Processing doc_id={doc_id}, file={file_name}, path={pdf_path}")
        
        # Set status to "In Progress" before processing
        update_document_status(doc_id, None, status="In Progress")
        
        # Send to extraction API
        result, error = send_to_extraction_api(pdf_path, client_id, format_id)
        
        if result and not error:
            # Success - update with extracted data
            update_document_status(doc_id, result, status="Completed")
            success_count += 1
        else:
            # Failed - update with error
            update_document_status(doc_id, None, status="Failed", error_msg=error)
            fail_count += 1
        
        # Small delay between requests
        time.sleep(0.5)
    
    return success_count, fail_count


# ============================================
# Main Loop - Runs Every 30 Seconds
# ============================================
def main_loop():
    """Main loop that runs every 30 seconds"""
    
    logger.info("=" * 50)
    logger.info("STARTING DOCUMENT PROCESSING WORKER")
    logger.info(f"Database: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}")
    logger.info(f"API Endpoint: {EXTRACTION_API_URL}")
    logger.info(f"Check Interval: {CHECK_INTERVAL} seconds")
    logger.info("=" * 50)
    
    total_success = 0
    total_failed = 0
    
    while True:
        try:
            # Process pending documents
            success, failed = process_pending()
            total_success += success
            total_failed += failed
            
            if success > 0 or failed > 0:
                logger.info(f"Batch done: Success={success}, Failed={failed} | Total: Success={total_success}, Failed={total_failed}")
            
        except Exception as e:
            logger.error(f"Error in processing loop: {e}")
        
        # Wait 30 seconds before next check
        logger.info(f"Sleeping for {CHECK_INTERVAL} seconds...")
        time.sleep(CHECK_INTERVAL)


# ============================================
# Entry Point
# ============================================
if __name__ == "__main__":
    # Create lock to prevent duplicate runs
    lock = SingleInstanceLock(LOCK_FILE)
    
    if not lock.acquire():
        print("Another instance is already running. Exiting.")
        logger.warning("Another instance is already running. Exiting.")
        sys.exit(0)
    
    try:
        main_loop()
    except KeyboardInterrupt:
        logger.info("\nProcess interrupted by user. Exiting.")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        lock.release()
        sys.exit(0)
