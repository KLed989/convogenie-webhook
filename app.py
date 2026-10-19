import hmac
import json
import logging
import os
import re
from flask import Flask, jsonify, request

app = Flask(__name__)

# Reject very large payloads before parsing.
app.config["MAX_CONTENT_LENGTH"] = 256 * 1024  # 256 KiB

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("convogenie_webhook")

API_KEY = os.getenv("CONVOGENIE_API_KEY", "")
MAX_DEPTH = 8
MAX_STRING_LENGTH = 10_000


def json_error(message, status):
    return jsonify({"ok": False, "error": message}), status


def valid_json_shape(value, depth=0):
    """Bound JSON complexity and reject unexpected Python types."""
    if depth > MAX_DEPTH:
        return False
    if isinstance(value, str):
        return len(value) <= MAX_STRING_LENGTH
    if value is None or isinstance(value, (bool, int, float)):
        return True
    if isinstance(value, list):
        return len(value) <= 1000 and all(valid_json_shape(v, depth + 1) for v in value)
    if isinstance(value, dict):
        return (
            len(value) <= 1000
            and all(isinstance(k, str) and len(k) <= 200 for k in value.keys())
            and all(valid_json_shape(v, depth + 1) for v in value.values())
        )
    return False


@app.get("/")
def index():
    return jsonify({
        "service": "convogenie-webhook",
        "status": "running",
        "mode": "test-only",
        "message": "Webhook service is online. Use POST /webhook to send a test event."
    }), 200


@app.get("/health")
def health():
    return jsonify({"ok": True, "status": "healthy"}), 200


@app.post("/webhook")
def webhook():
    # Fail closed if the server secret has not been configured.
    if not API_KEY:
        logger.error("Webhook rejected because CONVOGENIE_API_KEY is not configured")
        return json_error("Webhook authentication is not configured", 503)

    supplied_key = request.headers.get("X-Webhook-Secret", "")
    if not supplied_key or not hmac.compare_digest(supplied_key, API_KEY):
        return json_error("Unauthorized", 401)

    if not request.is_json:
        return json_error("Content-Type must be application/json", 415)

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return json_error("Request body must be a JSON object", 400)

    if not valid_json_shape(payload):
        return json_error("JSON payload is too large or complex", 400)

    # Do not log the body or personal lead data. This version only confirms
    # receipt; it does not persist data or integrate with the CRM yet.
    event_id = request.headers.get("X-Event-ID", "")
    if event_id and (len(event_id) > 200 or not re.fullmatch(r"[A-Za-z0-9._:-]+", event_id)):
        return json_error("Invalid X-Event-ID header", 400)

    logger.info("Accepted test webhook request; top_level_fields=%d; event_id_present=%s",
                len(payload), bool(event_id))

    return jsonify({
        "ok": True,
        "received": True,
        "mode": "test-only",
        "persisted": False,
        "crm_updated": False,
        "message": "Request received for testing only; no lead data was stored."
    }), 202


@app.errorhandler(413)
def too_large(_error):
    return json_error("Request body exceeds the 256 KiB limit", 413)


@app.errorhandler(400)
def bad_request(_error):
    return json_error("Invalid request", 400)


if __name__ == "__main__":
    # Render supplies PORT. Local default is for development only.
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
