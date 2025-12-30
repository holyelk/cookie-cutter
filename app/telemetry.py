from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from app.config import settings

def setup_telemetry(app_name):
    if not settings.enable_telemetry:
        return

    resource = Resource.create(attributes={"service.name": app_name, "environment": settings.environment})

    # Tracing
    trace_provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otlp_grpc_endpoint, insecure=True))
    trace_provider.add_span_processor(processor)
    trace.set_tracer_provider(trace_provider)

    # Metrics
    reader = PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=settings.otlp_grpc_endpoint, insecure=True))
    meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(meter_provider)
