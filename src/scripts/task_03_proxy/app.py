from __future__ import annotations

import logging
import os
from http import HTTPStatus

from flask import Flask, jsonify, request
from dotenv import load_dotenv
load_dotenv(".env.llm")

from src.scripts.task_03_proxy.orchestrator import ProxyOrchestrator
from src.scripts.task_03_proxy.packages_client import PackagesClient
from src.scripts.task_03_proxy.session_store import SessionStore
from src.scripts.task_03_proxy.trace import ProxyTraceLogger


def create_app() -> Flask:
    app = Flask(__name__)

    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    logger = logging.getLogger("task_03_proxy.app")


    session_store = SessionStore()
    trace_logger = ProxyTraceLogger()

    packages_client = PackagesClient(
        api_key=os.environ["AI_DEVS_API"],
        base_url=os.getenv("PACKAGES_API_URL", "https://hub.ag3nts.org/api/packages"),
    )

    orchestrator = ProxyOrchestrator(
        session_store=session_store,
        packages_client=packages_client,
        trace_logger=trace_logger,
    )

    @app.get("/health")
    def health() -> tuple[dict, int]:
        return {"status": "ok"}, HTTPStatus.OK

    @app.post("/")
    def proxy_endpoint():
        payload = request.get_json(silent=True)

        if payload is None:
            return (
                jsonify({"error": "Request body must be valid JSON"}),
                HTTPStatus.BAD_REQUEST,
            )

        session_id = payload.get("sessionID")
        msg = payload.get("msg")

        if not isinstance(session_id, str) or not session_id.strip():
            return (
                jsonify({"error": "Field 'sessionID' must be a non-empty string"}),
                HTTPStatus.BAD_REQUEST,
            )

        if not isinstance(msg, str) or not msg.strip():
            return (
                jsonify({"error": "Field 'msg' must be a non-empty string"}),
                HTTPStatus.BAD_REQUEST,
            )

        logger.info("Incoming request | sessionID=%s | msg=%s", session_id, msg)

        try:
            response_text = orchestrator.handle_message(
                session_id=session_id.strip(),
                user_message=msg.strip(),
            )
        except Exception as exc:
            logger.exception("Unhandled proxy error | sessionID=%s", session_id)
            return (
                jsonify({"error": "Internal server error", "details": str(exc)}),
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )

        return jsonify({"msg": response_text}), HTTPStatus.OK

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)