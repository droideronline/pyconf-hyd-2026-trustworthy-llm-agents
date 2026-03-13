"""OpenTelemetry instrumentation — sends LangGraph traces to self-hosted Langfuse.

Call ``setup_tracing()`` once at process startup, before any LangChain/LangGraph
objects are created.  Everything else is automatic: the LangSmith OTEL bridge
instruments every LLM call, tool invocation, and agent step via the standard
OpenTelemetry SDK.

Required env vars (set in .env):
    LANGFUSE_HOST        — e.g. http://localhost:4000
    LANGFUSE_PUBLIC_KEY  — e.g. pk-lf-pyconf-public
    LANGFUSE_SECRET_KEY  — e.g. sk-lf-pyconf-secret
"""

from __future__ import annotations

import base64
import logging
import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger(__name__)


def setup_tracing() -> None:
    """Configure the global OTEL TracerProvider to export spans to Langfuse.

    Safe to call multiple times — subsequent calls are no-ops once the provider
    is already configured.
    """
    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY", "").strip()
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY", "").strip()
    host = os.environ.get("LANGFUSE_HOST", "http://localhost:4000").rstrip("/")

    if not public_key or not secret_key:
        logger.warning(
            "LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY not set — tracing disabled."
        )
        return

    # Langfuse OTLP ingestion endpoint (v3 self-hosted)
    endpoint = f"{host}/api/public/otel/v1/traces"

    # Basic auth: base64(public_key:secret_key)
    token = base64.b64encode(f"{public_key}:{secret_key}".encode()).decode()
    headers = {"Authorization": f"Basic {token}"}

    service_name = os.environ.get("OTEL_SERVICE_NAME", "support-swarm")
    resource = Resource(attributes={SERVICE_NAME: service_name})

    exporter = OTLPSpanExporter(endpoint=endpoint, headers=headers)
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    # Enable automatic LangChain / LangGraph OTEL instrumentation.
    # The langsmith[otel] package hooks into every LLM call and tool invocation.
    os.environ["LANGSMITH_OTEL_ENABLED"] = "true"
    # Don't try to fan-out to LangSmith cloud (we have no API key).
    os.environ.setdefault("LANGSMITH_TRACING", "false")

    logger.info("Tracing enabled → %s (service: %s)", endpoint, service_name)
