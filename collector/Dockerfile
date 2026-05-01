FROM otel/opentelemetry-collector-contrib:0.151.0

COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:1.0.0 /lambda-adapter /opt/extensions/lambda-adapter

COPY config.yaml /etc/otel/config.yaml

ENV AWS_LWA_PORT=4318
ENV AWS_LWA_INVOKE_MODE=buffered
ENV AWS_LWA_READINESS_CHECK_PATH=/

ENTRYPOINT ["/otelcol-contrib"]
CMD ["--config=/etc/otel/config.yaml"]
