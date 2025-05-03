# How to use OpenTelemetry in a Python project

## Installing OpenTelemetry

These instructions assume we're using pip and requirements.txt

I've copied them from https://docs.honeycomb.io/send-data/python/opentelemetry-sdk/ on 03.05.2025

- first, make sure all your dependencies are in requirements.txt

```
pip freeze > requirements.txt
```

- Install the OpenTelemetry Python packages:

```
python -m pip install opentelemetry-instrumentation \
    opentelemetry-distro \
    opentelemetry-exporter-otlp
```

- Install instrumentation libraries for the packages used by your application

```
opentelemetry-bootstrap >> requirements.txt
pip install -r requirements.txt
```

- Configure the OpenTelemetry SDK to export data to Honeycomb

```
export OTEL_SERVICE_NAME="your-service-name"
export OTEL_TRACES_EXPORTER="otlp"
export OTEL_EXPORTER_OTLP_PROTOCOL="http/protobuf"
export OTEL_EXPORTER_OTLP_ENDPOINT="https://api.honeycomb.io:443"
export OTEL_EXPORTER_OTLP_HEADERS="x-honeycomb-team=$HONEYCOMB_API_KEY"
export OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED=true
```

Replace "your-service-name" with the name of the application.

- Whenever you run your application, wrap the execution with OpenTelemetry.

```
opentelemetry-instrument python your_application.py
```

If you use `flask` to run it, or whatever other wrapper, stick `opentelemetry-instrument` in front that.


## Customizing instrumentation

The automatic instrumentation installed above will create spans for outgoing network calls, incoming web requests etc.

Enhance this by adding custom attributes related to this application.

- install the API

```
pip install opentelemetry-api
pip freeze > requirements.txt
```

### Add attributes to spans

Do this frequently.

```python
from opentelemetry import trace

# ...

span = trace.get_current_span()
span.set_attribute("user.id", user.id())
```

### Create custom spans

Do this more rarely.

- Acquire a tracer

Do this once per module.

```python
from opentelemetry import trace

tracer = trace.get_tracer("module-name")
```

- Create spans around important methods with an annotation

```python
@tracer.start_as_current_span("do_work")
def do_work():
    # do some work ...
```

- Create spans around blocks

```python
with tracer.start_as_current_span("span-name"):
    ...
```

