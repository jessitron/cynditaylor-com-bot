# The contrib image is distroless + non-root, which Lambda's container runtime
# doesn't get along with. Stage the binary into Alpine. Critical detail learned
# from LWA's gin example: use CMD only, no ENTRYPOINT. Lambda's container init
# behaves differently when ENTRYPOINT is set — `app is not ready` loop with no
# main-process startup, init phase times out at 10 s.
FROM otel/opentelemetry-collector-contrib:0.151.0 AS collector

FROM alpine:3.20
RUN apk add --no-cache ca-certificates

COPY --from=collector /otelcol-contrib /app/otelcol-contrib
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:1.0.0 /lambda-adapter /opt/extensions/lambda-adapter
COPY config.yaml /etc/otel/config.yaml

ENV AWS_LWA_PORT=4318
ENV AWS_LWA_INVOKE_MODE=buffered
ENV AWS_LWA_READINESS_CHECK_PATH=/

CMD ["/app/otelcol-contrib", "--config=/etc/otel/config.yaml"]
