FROM python:3.12-alpine@sha256:4c47124a8391cb7a9f571164147d154777cf012a4ece5f86097130d7a4478111
RUN addgroup -g 65532 sandbox && adduser -D -H -u 65532 -G sandbox sandbox \
    && mkdir /source && chmod 755 /source
USER 65532:65532
WORKDIR /tmp
CMD ["python", "--version"]
