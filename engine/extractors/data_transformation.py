"""
Data Transformation Module
Transforms extracted invoice data based on mapping rules from database
Includes Flask API for managing transformation rules
"""
import logging
from typing import Dict, Any, Optional, List
import psycopg2
import select
import psycopg2.extensions
from psycopg2.extras import RealDictCursor
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
import os
from pathlib import Path
import time
import threading

logger = logging.getLogger(__name__)

# Database configuration
DB_CONFIG = {
    "dbname": "mydb",
    "user": "sql_developer",
    "password": "Dev@123",
    "host": "103.14.123.44",
    "port": 5432,
}

# Uvicorn reload trigger configuration
# When a transformation is created/updated/deleted we touch a file so
# an external uvicorn process started with --reload (or a watcher) will restart.
UVICORN_AUTO_RELOAD_ON_WRITE = os.environ.get("UVICORN_AUTO_RELOAD_ON_WRITE", "1").lower() in ("1", "true", "yes")
# Resolve repository root relative to this file so multiple processes see the
# same default trigger/marker paths even if their current working directory
# differs (common in containerized or supervised setups).
try:
    REPO_ROOT = Path(__file__).resolve().parents[3]
except Exception:
    REPO_ROOT = Path.cwd()

# By default trigger a file in the repository root. Touching the module file
# itself can sometimes not be observed by external watchers (container mounts,
# different working dirs). Using a dedicated trigger file under the repo root
# is more reliable for uvicorn/watchers. Override with env var if needed.
UVICORN_RELOAD_TRIGGER_FILE = os.environ.get(
    "UVICORN_RELOAD_TRIGGER_FILE", str(REPO_ROOT / ".uvicorn_reload_trigger")
)
# Marker file touched by API handlers to notify other processes to reload mappings.
# This is independent of the uvicorn reload trigger and is used so other running
# processes can detect mapping changes and refresh their in-memory cache.
UVICORN_UPDATE_MARKER_FILE = os.environ.get("UVICORN_UPDATE_MARKER_FILE", str(REPO_ROOT / ".transformations_updated"))
# Optional: force the process to exit after write so a supervising reload watcher
# (uvicorn --reload master process or external supervisor) will fully restart.
# Set to "1" or "true" to enable.
UVICORN_FORCE_RESTART_ON_WRITE = os.environ.get("UVICORN_FORCE_RESTART_ON_WRITE", "0").lower() in ("1", "true", "yes")

# Debounce window (seconds) to avoid multiple rapid touches/exits
_RELOAD_DEBOUNCE_SECONDS = float(os.environ.get("UVICORN_RELOAD_DEBOUNCE_SECONDS", "1.0"))
_last_reload_time = 0.0

def _trigger_uvicorn_reload():
    """Touch the configured trigger file to update mtime and notify file-watchers.

    This is a best-effort helper — it will not raise on failure.
    """
    if not UVICORN_AUTO_RELOAD_ON_WRITE:
        logger.debug("[uvicorn-reload] Auto-reload on write is disabled by environment flag")
        return
    global _last_reload_time
    try:
        now = time.time()
        if now - _last_reload_time < _RELOAD_DEBOUNCE_SECONDS:
            logger.debug("[uvicorn-reload] Debounced reload trigger (skipping)")
            return

        # Try multiple candidate trigger files to increase reliability across
        # different deployment/watch setups. Order: configured file, repo-root
        # .uvicorn_reload_trigger, and finally this module file.
        candidates = []
        try:
            candidates.append(Path(UVICORN_RELOAD_TRIGGER_FILE))
        except Exception:
            pass
        try:
            candidates.append(REPO_ROOT / ".uvicorn_reload_trigger")
        except Exception:
            pass
        try:
            candidates.append(Path(__file__).resolve())
        except Exception:
            pass
        # Debug: log candidate status (exists & mtime) before touching
        try:
            candidate_info = []
            for cp in candidates:
                try:
                    exists = cp.exists()
                    mtime = cp.stat().st_mtime if exists else None
                except Exception:
                    exists = False
                    mtime = None
                candidate_info.append({"path": str(cp), "exists": exists, "mtime": mtime})
            logger.debug(f"[uvicorn-reload] Candidate trigger files: {candidate_info}")
        except Exception:
            logger.debug("[uvicorn-reload] Failed to gather candidate trigger file info", exc_info=True)

        touched_any = False
        for p in candidates:
            try:
                if not p.exists():
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_text("")
                os.utime(str(p), (now, now))
                # Also update parent directory mtime as a fallback for some watchers
                try:
                    os.utime(str(p.parent), (now, now))
                except Exception:
                    pass
                # Log the mtime after touch for diagnostics
                try:
                    post_mtime = p.stat().st_mtime
                except Exception:
                    post_mtime = None
                logger.info(f"[uvicorn-reload] Touched reload trigger file: {p} (post_mtime={post_mtime})")
                touched_any = True
            except Exception:
                logger.debug(f"[uvicorn-reload] Failed to touch candidate trigger file: {p}", exc_info=True)

        if touched_any:
            _last_reload_time = now
        else:
            logger.warning("[uvicorn-reload] No trigger file could be touched")
    except Exception:
        logger.exception("[uvicorn-reload] Failed to touch reload trigger file")


def _touch_update_marker():
    """Touch the transformations-updated marker file so other processes can detect changes.

    This is used by API handlers immediately after committing DB changes to signal
    other running processes to reload their in-memory caches.
    """
    try:
        p = Path(UVICORN_UPDATE_MARKER_FILE)
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("")
        # Capture previous mtime for debugging (if present)
        try:
            prev_mtime = p.stat().st_mtime if p.exists() else None
        except Exception:
            prev_mtime = None
        now = time.time()
        os.utime(str(p), (now, now))
        try:
            new_mtime = p.stat().st_mtime
        except Exception:
            new_mtime = now
        logger.info(f"[transformations-marker] Touched update marker file: {p} (prev_mtime={prev_mtime}, new_mtime={new_mtime})")
    except Exception:
        logger.exception("[transformations-marker] Failed to touch update marker file")


def _gather_marker_and_trigger_status() -> Dict[str, Any]:
    """Return diagnostic information about the update marker and trigger candidates.

    Useful for cross-process debugging via a debug endpoint.
    """
    status: Dict[str, Any] = {}
    try:
        mp = Path(UVICORN_UPDATE_MARKER_FILE)
        status['marker_path'] = str(mp)
        try:
            status['marker_exists'] = mp.exists()
        except Exception:
            status['marker_exists'] = False
        try:
            status['marker_mtime'] = mp.stat().st_mtime if status['marker_exists'] else None
        except Exception:
            status['marker_mtime'] = None
    except Exception:
        status['marker_path'] = str(UVICORN_UPDATE_MARKER_FILE)
        status['marker_exists'] = False
        status['marker_mtime'] = None

    # Candidate trigger files
    try:
        candidates = [Path(UVICORN_RELOAD_TRIGGER_FILE), REPO_ROOT / ".uvicorn_reload_trigger", Path(__file__).resolve()]
    except Exception:
        candidates = [Path(UVICORN_RELOAD_TRIGGER_FILE)]

    candidate_list = []
    for cp in candidates:
        try:
            exists = cp.exists()
        except Exception:
            exists = False
        try:
            mtime = cp.stat().st_mtime if exists else None
        except Exception:
            mtime = None
        candidate_list.append({"path": str(cp), "exists": exists, "mtime": mtime})

    status['trigger_candidates'] = candidate_list
    return status


def invalidate_transformer_singleton():
    """Invalidate the module-level DataTransformer singleton so next caller
    will create a fresh instance (reloading transformations and DB state).

    This helps when update operations run in one process/thread and other
    parts of the app (or worker threads) rely on the module-level singleton
    and may not pick up in-memory mutations.
    """
    global _transformer_instance
    try:
        _transformer_instance = None
        logger.info("[transformations] Invalidated transformer singleton; next get_transformer() will recreate it")
    except Exception:
        logger.exception("[transformations] Failed to invalidate transformer singleton")


def _maybe_force_restart():
    """If configured, schedule a background exit to force a full restart.

    This runs in a daemon thread so the current request can finish. It calls
    os._exit(0) after a short sleep. Only enabled when
    `UVICORN_FORCE_RESTART_ON_WRITE` is truthy.
    """
    if not UVICORN_FORCE_RESTART_ON_WRITE:
        return

    def _exit_later():
        try:
            # small delay to allow response to be sent
            time.sleep(0.5)
            logger.info("[uvicorn-reload] Forcing process exit to trigger supervisor/uvicorn reload")
            os._exit(0)
        except Exception:
            logger.exception("[uvicorn-reload] Failed to force process exit")

    t = threading.Thread(target=_exit_later, name="uvicorn-force-restart", daemon=True)
    t.start()


def _schedule_reload_after_response(delay: float = 0.1):
    """Schedule the reload trigger to run in a short background thread.

    This ensures DB commit and the HTTP response are not blocked by touching
    the trigger file or forcing a process exit. The default small delay
    gives the WSGI server a moment to flush the response.
    """
    def _worker():
        try:
            time.sleep(delay)
            try:
                _trigger_uvicorn_reload()
            except Exception:
                logger.debug("Failed to trigger uvicorn reload (scheduled)", exc_info=True)

            try:
                _maybe_force_restart()
            except Exception:
                logger.debug("Failed to run force-restart helper (scheduled)", exc_info=True)
        except Exception:
            logger.exception("[uvicorn-reload] Scheduled reload worker failed")

    t = threading.Thread(target=_worker, name="uvicorn-reload-scheduler", daemon=True)
    t.start()
class DataTransformer:
    """Handles data transformation based on database mapping rules"""
    
    def __init__(self, db_config: Dict[str, Any] = None):
        """Initialize with database configuration"""
        self.db_config = db_config or DB_CONFIG
        self._transformation_cache = None
        # track marker mtime so we can detect updates from other processes
        self._last_marker_mtime = 0.0
        # track last observed DB timestamp so polling can detect external changes
        self._last_db_timestamp = 0.0
        self._load_transformations()
        # Start a background listener for DB NOTIFY messages so this process
        # can react to transformation updates made by other processes/containers.
        try:
            self._start_db_listener()
        except Exception:
            logger.debug("Failed to start DB listener thread", exc_info=True)
        # Also start a lightweight DB polling thread to catch updates when
        # external writers do not emit NOTIFY (e.g. proxy inserts directly).
        try:
            self._start_db_polling()
        except Exception:
            logger.debug("Failed to start DB polling thread", exc_info=True)
    
    def _load_transformations(self) -> None:
        """Load transformation mappings from database"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Query to get all transformation rules
            query = """
                SELECT field_name, from_value, to_value 
                FROM data_transformation 
                ORDER BY field_name, from_value
            """
            cursor.execute(query)
            rows = cursor.fetchall()
            
            # Build cache: {field_name: {from_value: to_value}}
            self._transformation_cache = {}
            for row in rows:
                field_name = row['field_name']
                from_value = row['from_value']
                to_value = row['to_value']
                
                if field_name not in self._transformation_cache:
                    self._transformation_cache[field_name] = {}
                
                self._transformation_cache[field_name][from_value] = to_value
            
            cursor.close()
            conn.close()
            
            logger.info(f"Loaded {len(rows)} transformation rules for {len(self._transformation_cache)} fields")
            
        except Exception as e:
            logger.error(f"Failed to load transformations from database: {e}")
            self._transformation_cache = {}
    
    def transform_value(self, field_name: str, value: Any) -> tuple[Any, bool]:
        """
        Transform a single field value based on mapping rules
        
        Args:
            field_name: Name of the field (e.g., 'Vehicle', 'Destination', 'Consignee')
            value: Original extracted value
        
        Returns:
            tuple: (transformed_value, was_changed)
        """
        if not value or not isinstance(value, str):
            return value, False
        
        # Check if we have transformations for this field
        if field_name not in self._transformation_cache:
            return value, False
        
        # Check if this value needs transformation
        field_mappings = self._transformation_cache[field_name]
        if value in field_mappings:
            transformed = field_mappings[value]
            logger.info(f"Transformed {field_name}: '{value}' -> '{transformed}'")
            return transformed, True
            
        # Selective fuzzy matching: only apply to specific fields
        # Fields that allow fuzzy matching (80-90% threshold): Branch, Source, Destination, Consignor, Consignee
        fuzzy_enabled_fields = {'Branch', 'Source', 'Destination', 'Consignor', 'Consignee'}
        
        if field_name in fuzzy_enabled_fields:
            import difflib
            best_match = None
            best_ratio = 0.0
            
            for from_val in field_mappings:
                # Skip empty strings to avoid division by zero or useless matches
                if not from_val:
                    continue
                    
                ratio = difflib.SequenceMatcher(None, value.lower(), from_val.lower()).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_match = from_val
            
            # Use 80% threshold (0.80) for fuzzy matching
            if best_ratio >= 0.80:
                transformed = field_mappings[best_match]
                logger.info(f"Fuzzy Transformed {field_name}: '{value}' -> '{transformed}' (match='{best_match}', score={best_ratio:.2f})")
                return transformed, True
        
        return value, False
    
    def transform_data(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform all applicable fields in extracted data
        
        Args:
            extracted_data: Dictionary of extracted invoice data
        
        Returns:
            Dictionary with transformed data and metadata about changes
        """
        if not extracted_data:
            return {
                "data": extracted_data,
                "transformed": False,
                "changes": []
            }
        
        # Before transforming, check whether an external update marker was touched
        # by the API process. If so, reload transformations so this process uses
        # the latest mappings.
        try:
            self._maybe_reload_from_marker()
        except Exception:
            logger.debug("Failed to check update marker before transform", exc_info=True)

        transformed_data = extracted_data.copy()
        changes = []
        
        # Fields that can be transformed based on your CSV
        transformable_fields = [
            "Vehicle", "vehicle_number", "vehicle",
            "Destination", "destination",
            "Consignee", "consignee", "consignee_name"
        ]
        
        for field in transformable_fields:
            if field in transformed_data:
                original_value = transformed_data[field]
                
                # Try transformation with exact field name first
                transformed_value, changed = self.transform_value(field, original_value)
                
                # If not found, try with capitalized version
                if not changed and field.lower() != field:
                    transformed_value, changed = self.transform_value(
                        field.capitalize(), 
                        original_value
                    )
                
                if changed:
                    transformed_data[field] = transformed_value
                    changes.append({
                        "field": field,
                        "from": original_value,
                        "to": transformed_value
                    })
        
        result = {
            "data": transformed_data,
            "transformed": len(changes) > 0,
            "changes": changes
        }
        
        if changes:
            logger.info(f"Data transformation complete: {len(changes)} field(s) changed")
        else:
            logger.info("No data transformations needed")
        
        return result
    
    def reload_transformations(self) -> None:
        """Reload transformation rules from database (useful if mappings are updated)"""
        logger.info("Reloading transformation rules...")
        self._load_transformations()

    def _start_db_listener(self):
        """Start a daemon thread that LISTENs for Postgres NOTIFY messages.

        When a `transformations_updated` notification is received this process
        will reload its in-memory mappings.
        """
        def _listener():
            try:
                conn = psycopg2.connect(**self.db_config)
                # Required to receive notifications outside of transactions
                conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
                cur = conn.cursor()
                try:
                    cur.execute("LISTEN transformations_updated;")
                except Exception:
                    logger.exception("Failed to execute LISTEN on transformations_updated")
                    cur.close()
                    conn.close()
                    return

                logger.info("Started DB LISTEN for transformations_updated notifications")
                while True:
                    try:
                        # Use select to wait for notifications (timeout to allow clean exit)
                        if select.select([conn], [], [], 5) == ([], [], []):
                            continue
                        conn.poll()
                        while conn.notifies:
                            notify = conn.notifies.pop(0)
                            logger.info(f"Received DB notification: {notify.channel} {notify.payload}")
                            try:
                                self.reload_transformations()
                            except Exception:
                                logger.exception("Failed to reload transformations after DB notify")
                    except Exception:
                        logger.exception("DB listener loop failed; retrying in 2s")
                        time.sleep(2)
            except Exception:
                logger.exception("DB listener thread failed to start")

        t = threading.Thread(target=_listener, name="transformations-db-listener", daemon=True)
        t.start()

    def _start_db_polling(self):
        """Start a daemon thread that polls the DB for changes to transformations.

        This is a fallback for environments where NOTIFY/LISTEN may not be
        delivered (for example when writes happen via a proxy that doesn't
        forward notifications or when a DB pooler interferes). The poller
        checks MAX(COALESCE(updated_at, created_at)) and reloads when it
        observes a newer timestamp.
        """
        # Poll interval configurable via env var (seconds)
        poll_interval = float(os.environ.get("TRANSFORMATIONS_POLL_INTERVAL", "5.0"))

        def _poller():
            try:
                # Initialize last seen timestamp from DB if available
                try:
                    conn = psycopg2.connect(**self.db_config)
                    cur = conn.cursor()
                    cur.execute("SELECT MAX(COALESCE(updated_at, created_at)) FROM data_transformation")
                    row = cur.fetchone()
                    conn.close()
                    if row and row[0]:
                        try:
                            self._last_db_timestamp = float(row[0].timestamp())
                        except Exception:
                            # fallback to 0 on weird types
                            self._last_db_timestamp = 0.0
                except Exception:
                    # If initial read fails, continue polling from zero
                    logger.debug("[db-poll] Initial timestamp read failed", exc_info=True)

                while True:
                    try:
                        conn = psycopg2.connect(**self.db_config)
                        cur = conn.cursor()
                        cur.execute("SELECT MAX(COALESCE(updated_at, created_at)) FROM data_transformation")
                        row = cur.fetchone()
                        conn.close()

                        new_ts = 0.0
                        if row and row[0]:
                            try:
                                new_ts = float(row[0].timestamp())
                            except Exception:
                                new_ts = 0.0

                        # If DB has a newer timestamp, reload transformations
                        if new_ts > getattr(self, "_last_db_timestamp", 0.0):
                            logger.info(f"[db-poll] Detected transformation table change (ts={new_ts}); reloading")
                            try:
                                self.reload_transformations()
                                self._last_db_timestamp = new_ts
                            except Exception:
                                logger.exception("[db-poll] Failed to reload transformations after detecting DB change")

                        time.sleep(poll_interval)
                    except Exception:
                        logger.exception("[db-poll] Polling loop failed; sleeping and retrying")
                        time.sleep(poll_interval)
            except Exception:
                logger.exception("[db-poll] Poller failed to start")

        t = threading.Thread(target=_poller, name="transformations-db-poller", daemon=True)
        t.start()

    def _maybe_reload_from_marker(self) -> None:
        """Check the marker file and reload transformations if it's newer than last seen.

        This allows other running processes to react to updates made by the API
        without requiring a full process/container restart.
        """
        try:
            p = Path(UVICORN_UPDATE_MARKER_FILE)
            if not p.exists():
                logger.debug(f"[transformations-marker] Marker file does not exist: {p}")
                return
            try:
                mtime = p.stat().st_mtime
            except Exception:
                logger.exception("[transformations-marker] Failed to stat marker file")
                return

            prev = getattr(self, "_last_marker_mtime", 0.0)
            logger.debug(f"[transformations-marker] Observed marker mtime: {mtime} (previously: {prev})")
            if mtime > prev:
                logger.info("[transformations-marker] Detected external update marker; reloading transformations")
                self._load_transformations()
                self._last_marker_mtime = mtime
            else:
                logger.debug("[transformations-marker] Marker mtime not newer; no reload needed")
        except Exception:
            logger.exception("[transformations-marker] Error checking or reloading from marker")


# Singleton instance for easy import
_transformer_instance = None

def get_transformer() -> DataTransformer:
    """Get or create the singleton DataTransformer instance"""
    global _transformer_instance
    if _transformer_instance is None:
        _transformer_instance = DataTransformer()
    return _transformer_instance


def transform_extracted_data(extracted_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to transform extracted data
    
    Args:
        extracted_data: Dictionary of extracted invoice data
    
    Returns:
        Dictionary with transformed data and metadata
    """
    transformer = get_transformer()
    return transformer.transform_data(extracted_data)


# ============================================
# Flask API for Transformation Management
# ============================================

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend access


# Log every incoming request (method, path, remote addr, short body) for debugging
@app.before_request
def log_incoming_request():
    try:
        # Remote addr may be proxied; use X-Forwarded-For if present
        remote = request.headers.get('X-Forwarded-For', request.remote_addr)
        body = None
        try:
            # read raw data but avoid huge dumps
            body = request.get_data(cache=True, as_text=True)
        except Exception:
            body = None
        short = (body[:1000] + '...') if body and len(body) > 1000 else (body or '')
        logger.info(f"[http] {remote} -> {request.method} {request.path} body={short}")
    except Exception:
        logger.exception("Failed to log incoming request")


@app.route('/api/transformations', methods=['GET'])
def get_all_transformations():
    """
    Get all transformation rules from database
    
    Returns:
        JSON array of all transformation rules
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
            SELECT id, field_name, from_value, to_value, created_at, updated_at
            FROM data_transformation
            ORDER BY field_name, from_value
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # Convert datetime objects to strings
        result = []
        for row in rows:
            result.append({
                'id': row['id'],
                'field_name': row['field_name'],
                'from_value': row['from_value'],
                'to_value': row['to_value'],
                'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None
            })
        
        return jsonify({
            'success': True,
            'data': result,
            'count': len(result)
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to fetch transformations: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/transformations/<int:transformation_id>', methods=['GET'])
def get_transformation(transformation_id):
    """
    Get a single transformation rule by ID
    
    Args:
        transformation_id: ID of the transformation rule
    
    Returns:
        JSON object of the transformation rule
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
            SELECT id, field_name, from_value, to_value, created_at, updated_at
            FROM data_transformation
            WHERE id = %s
        """
        cursor.execute(query, (transformation_id,))
        row = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if not row:
            return jsonify({
                'success': False,
                'error': 'Transformation not found'
            }), 404
        
        result = {
            'id': row['id'],
            'field_name': row['field_name'],
            'from_value': row['from_value'],
            'to_value': row['to_value'],
            'created_at': row['created_at'].isoformat() if row['created_at'] else None,
            'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None
        }
        
        return jsonify({
            'success': True,
            'data': result
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to fetch transformation: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/transformations/field/<field_name>', methods=['GET'])
def get_transformations_by_field(field_name):
    """
    Get all transformation rules for a specific field
    
    Args:
        field_name: Name of the field (e.g., 'Vehicle', 'Destination', 'Consignee')
    
    Returns:
        JSON array of transformation rules for the field
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
            SELECT id, field_name, from_value, to_value, created_at, updated_at
            FROM data_transformation
            WHERE field_name = %s
            ORDER BY from_value
        """
        cursor.execute(query, (field_name,))
        rows = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        result = []
        for row in rows:
            result.append({
                'id': row['id'],
                'field_name': row['field_name'],
                'from_value': row['from_value'],
                'to_value': row['to_value'],
                'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None
            })
        
        return jsonify({
            'success': True,
            'data': result,
            'count': len(result)
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to fetch transformations by field: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/transformations', methods=['POST'])
def create_transformation():
    """
    Create a new transformation rule
    
    Request Body:
        {
            "field_name": "Vehicle",
            "from_value": "TN12AB3456",
            "to_value": "TN34CD7890"
        }
    
    Returns:
        JSON object with created transformation
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body is required'
            }), 400
        
        field_name = data.get('field_name')
        from_value = data.get('from_value')
        to_value = data.get('to_value')
        
        if not all([field_name, from_value, to_value]):
            return jsonify({
                'success': False,
                'error': 'field_name, from_value, and to_value are required'
            }), 400
        
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
            INSERT INTO data_transformation (field_name, from_value, to_value, created_at, updated_at)
            VALUES (%s, %s, %s, NOW(), NOW())
            RETURNING id, field_name, from_value, to_value, created_at, updated_at
        """
        cursor.execute(query, (field_name, from_value, to_value))
        row = cursor.fetchone()
        
        conn.commit()
        logger.info("[transformations] DB commit complete (create)")
        # Use a fresh autocommit connection to send NOTIFY so delivery
        # is not affected by transaction state or pooled connections.
        try:
            logger.info("[transformations] Attempting fresh NOTIFY (create)")
            nc = psycopg2.connect(**DB_CONFIG)
            nc.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            ncur = nc.cursor()
            ncur.execute("NOTIFY transformations_updated")
            logger.info("Sent NOTIFY transformations_updated (post-insert) via fresh connection")
            ncur.close()
            nc.close()
        except Exception:
            logger.exception("Failed to send NOTIFY (post-insert) via fresh connection")
        cursor.close()
        conn.close()
        
        # Reload transformations in memory
        get_transformer().reload_transformations()
        # Touch the shared update marker so other running processes detect the change
        try:
            _touch_update_marker()
        except Exception:
            logger.debug("Failed to touch update marker after create", exc_info=True)
        # Schedule reload trigger (non-blocking) so response isn't delayed
        try:
            _schedule_reload_after_response()
        except Exception:
            logger.debug("Failed to schedule uvicorn reload after create", exc_info=True)
        # Invalidate singleton so other importers/processes will recreate transformer
        try:
            invalidate_transformer_singleton()
        except Exception:
            logger.debug("Failed to invalidate transformer singleton after create", exc_info=True)
        # Additionally, perform an immediate best-effort reload trigger so other
        # watchers/processes see the update quickly. This is non-fatal if it fails.
        try:
            _trigger_uvicorn_reload()
        except Exception:
            logger.debug("Immediate trigger_uvicorn_reload() failed after create", exc_info=True)
        try:
            _maybe_force_restart()
        except Exception:
            logger.debug("Immediate maybe_force_restart() failed after create", exc_info=True)
        
        result = {
            'id': row['id'],
            'field_name': row['field_name'],
            'from_value': row['from_value'],
            'to_value': row['to_value'],
            'created_at': row['created_at'].isoformat() if row['created_at'] else None,
            'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None
        }
        
        return jsonify({
            'success': True,
            'data': result,
            'message': 'Transformation created successfully'
        }), 201
        
    except Exception as e:
        logger.error(f"Failed to create transformation: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/transformations/<int:transformation_id>', methods=['PUT'])
def update_transformation(transformation_id):
    """
    Update an existing transformation rule
    
    Args:
        transformation_id: ID of the transformation to update
    
    Request Body:
        {
            "field_name": "Vehicle",
            "from_value": "TN12AB3456",
            "to_value": "TN34CD7890"
        }
    
    Returns:
        JSON object with updated transformation
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body is required'
            }), 400
        
        field_name = data.get('field_name')
        from_value = data.get('from_value')
        to_value = data.get('to_value')
        
        if not all([field_name, from_value, to_value]):
            return jsonify({
                'success': False,
                'error': 'field_name, from_value, and to_value are required'
            }), 400
        
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
            UPDATE data_transformation
            SET field_name = %s, from_value = %s, to_value = %s, updated_at = NOW()
            WHERE id = %s
            RETURNING id, field_name, from_value, to_value, created_at, updated_at
        """
        cursor.execute(query, (field_name, from_value, to_value, transformation_id))
        row = cursor.fetchone()
        
        if not row:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Transformation not found'
            }), 404
        
        conn.commit()
        logger.info("[transformations] DB commit complete (update)")
        # Use a fresh autocommit connection to send NOTIFY so delivery
        # is not affected by transaction state or pooled connections.
        try:
            logger.info("[transformations] Attempting fresh NOTIFY (update)")
            nc = psycopg2.connect(**DB_CONFIG)
            nc.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            ncur = nc.cursor()
            ncur.execute("NOTIFY transformations_updated")
            logger.info("Sent NOTIFY transformations_updated (post-update) via fresh connection")
            ncur.close()
            nc.close()
        except Exception:
            logger.exception("Failed to send NOTIFY (post-update) via fresh connection")
        cursor.close()
        conn.close()
        
        # Reload transformations in memory
        get_transformer().reload_transformations()
        # Touch the shared update marker so other running processes detect the change
        try:
            _touch_update_marker()
        except Exception:
            logger.debug("Failed to touch update marker after update", exc_info=True)
        # Schedule reload trigger (non-blocking) so response isn't delayed
        try:
            _schedule_reload_after_response()
        except Exception:
            logger.debug("Failed to schedule uvicorn reload after update", exc_info=True)
        # Invalidate singleton so other importers/processes will recreate transformer
        try:
            invalidate_transformer_singleton()
        except Exception:
            logger.debug("Failed to invalidate transformer singleton after update", exc_info=True)
        # Immediate best-effort reload + optional forced restart
        try:
            _trigger_uvicorn_reload()
        except Exception:
            logger.debug("Immediate trigger_uvicorn_reload() failed after update", exc_info=True)
        try:
            _maybe_force_restart()
        except Exception:
            logger.debug("Immediate maybe_force_restart() failed after update", exc_info=True)

        result = {
            'id': row['id'],
            'field_name': row['field_name'],
            'from_value': row['from_value'],
            'to_value': row['to_value'],
            'created_at': row['created_at'].isoformat() if row['created_at'] else None,
            'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None
        }
        
        return jsonify({
            'success': True,
            'data': result,
            'message': 'Transformation updated successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to update transformation: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/transformations/<int:transformation_id>', methods=['DELETE'])
def delete_transformation(transformation_id):
    """
    Delete a transformation rule
    
    Args:
        transformation_id: ID of the transformation to delete
    
    Returns:
        JSON success message
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        query = "DELETE FROM data_transformation WHERE id = %s RETURNING id"
        cursor.execute(query, (transformation_id,))
        row = cursor.fetchone()
        
        if not row:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Transformation not found'
            }), 404
        
        conn.commit()
        logger.info("[transformations] DB commit complete (delete)")
        # Use a fresh autocommit connection to send NOTIFY so delivery
        # is not affected by transaction state or pooled connections.
        try:
            logger.info("[transformations] Attempting fresh NOTIFY (delete)")
            nc = psycopg2.connect(**DB_CONFIG)
            nc.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            ncur = nc.cursor()
            ncur.execute("NOTIFY transformations_updated")
            logger.info("Sent NOTIFY transformations_updated (post-delete) via fresh connection")
            ncur.close()
            nc.close()
        except Exception:
            logger.exception("Failed to send NOTIFY (post-delete) via fresh connection")
        cursor.close()
        conn.close()
        
        # Reload transformations in memory
        get_transformer().reload_transformations()
        # Touch the shared update marker so other running processes detect the change
        try:
            _touch_update_marker()
        except Exception:
            logger.debug("Failed to touch update marker after delete", exc_info=True)
        # Schedule reload trigger (non-blocking) so response isn't delayed
        try:
            _schedule_reload_after_response()
        except Exception:
            logger.debug("Failed to schedule uvicorn reload after delete", exc_info=True)
        # Invalidate singleton so other importers/processes will recreate transformer
        try:
            invalidate_transformer_singleton()
        except Exception:
            logger.debug("Failed to invalidate transformer singleton after delete", exc_info=True)
        # Immediate best-effort reload + optional forced restart
        try:
            _trigger_uvicorn_reload()
        except Exception:
            logger.debug("Immediate trigger_uvicorn_reload() failed after delete", exc_info=True)
        try:
            _maybe_force_restart()
        except Exception:
            logger.debug("Immediate maybe_force_restart() failed after delete", exc_info=True)

        return jsonify({
            'success': True,
            'message': 'Transformation deleted successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to delete transformation: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/transformations/reload', methods=['POST'])
def reload_cache():
    """
    Reload transformation cache from database
    
    Returns:
        JSON success message with count of loaded transformations
    """
    try:
        transformer = get_transformer()
        transformer.reload_transformations()
        
        # Touch the shared update marker so other running processes detect the change
        try:
            _touch_update_marker()
        except Exception:
            logger.debug("Failed to touch update marker after explicit reload", exc_info=True)
        # Schedule reload trigger (non-blocking) so response isn't delayed
        try:
            _schedule_reload_after_response()
        except Exception:
            logger.debug("Failed to schedule uvicorn reload after explicit reload", exc_info=True)

        count = sum(len(mappings) for mappings in transformer._transformation_cache.values())
        
        return jsonify({
            'success': True,
            'message': 'Transformation cache reloaded successfully',
            'count': count
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to reload cache: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/transformations/marker', methods=['GET'])
def get_marker_status():
    """Debug endpoint: return marker + trigger candidate status for troubleshooting.

    Returns JSON with `marker_path`, `marker_exists`, `marker_mtime`, and
    a `trigger_candidates` list with path/existence/mtime for each candidate.
    """
    try:
        status = _gather_marker_and_trigger_status()
        return jsonify({'success': True, 'data': status}), 200
    except Exception as e:
        logger.exception("Failed to gather marker status")
        return jsonify({'success': False, 'error': str(e)}), 500


# Note: Periodic/timer-based reload removed. Transformations are reloaded
# on-demand when POST/PUT/DELETE endpoints modify the DB (see create/update/delete handlers).


@app.route('/api/transformations/stats', methods=['GET'])
def get_stats():
    """
    Get statistics about transformations
    
    Returns:
        JSON object with statistics
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get total count
        cursor.execute("SELECT COUNT(*) as total FROM data_transformation")
        total = cursor.fetchone()['total']
        
        # Get count by field
        cursor.execute("""
            SELECT field_name, COUNT(*) as count
            FROM data_transformation
            GROUP BY field_name
            ORDER BY field_name
        """)
        by_field = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'total': total,
                'by_field': [{'field': row['field_name'], 'count': row['count']} for row in by_field]
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Health check endpoint
    
    Returns:
        JSON object with service status
    """
    try:
        # Test database connection
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'status': 'healthy',
            'database': 'connected'
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e)
        }), 500


def run_api(host='0.0.0.0', port=30019, debug=False):
    """
    Run the Flask API server
    
    Args:
        host: Host address (default: 0.0.0.0 for all interfaces)
        port: Port number (default: 5001)
        debug: Enable debug mode (default: False)
    """
    logger.info(f"Starting Data Transformation API on {host}:{port}")
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    import argparse
    
    # Setup argument parser
    parser = argparse.ArgumentParser(description="Data Transformation Module")
    parser.add_argument(
        '--api',
        action='store_true',
        help='Run Flask API server'
    )
    parser.add_argument(
        '--host',
        default='0.0.0.0',
        help='API host address (default: 0.0.0.0)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=5001,
        help='API port number (default: 5001)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode for API'
    )
    # Note: timer-based auto-reload removed. Use the POST/PUT/DELETE endpoints to trigger reloads.
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='[%(levelname)s] %(message)s'
    )
    
    if args.api:
        # Run Flask API
        print("=" * 60)
        print("DATA TRANSFORMATION API SERVER")
        print("=" * 60)
        print(f"Starting API on http://{args.host}:{args.port}")
        print("\nAvailable endpoints:")
        print("  GET    /api/transformations              - Get all transformations")
        print("  GET    /api/transformations/<id>         - Get transformation by ID")
        print("  GET    /api/transformations/field/<name> - Get by field name")
        print("  POST   /api/transformations              - Create new transformation")
        print("  PUT    /api/transformations/<id>         - Update transformation")
        print("  DELETE /api/transformations/<id>         - Delete transformation")
        print("  POST   /api/transformations/reload       - Reload cache")
        print("  GET    /api/transformations/stats        - Get statistics")
        print("  GET    /api/health                       - Health check")
        print("\n" + "=" * 60)
        
        run_api(host=args.host, port=args.port, debug=args.debug)
    else:
        # Test the transformer
        print("=" * 60)
        print("DATA TRANSFORMATION TEST")
        print("=" * 60)
        
        # Test data
        test_data = {
            "Vehicle": "TN73BZ7332",
            "Destination": "ARAKONAM",
            "Consignee": "K.S. TRADERS",
            "other_field": "some value"
        }
        
        print("\nOriginal data:")
        print(test_data)
        print("\nTransforming...")
        
        result = transform_extracted_data(test_data)
        
        print("\nTransformed data:")
        print(result["data"])
        print(f"\nWas transformed: {result['transformed']}")
        print(f"Changes made: {len(result['changes'])}")
        
        if result['changes']:
            print("\nChanges:")
            for change in result['changes']:
                print(f"  {change['field']}: '{change['from']}' -> '{change['to']}'")
        
        print("\n" + "=" * 60)
        print("TIP: Run with --api flag to start the API server")
        print("Example: python data_transformation.py --api --port 5001")
        print("=" * 60)

