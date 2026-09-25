FROM node:24-alpine@sha256:ebfe2f90462722a7a4de65e91990e97fe0d401c70e0e762c5b53302f905ec1c1
RUN addgroup -g 65532 sandbox && adduser -D -H -u 65532 -G sandbox sandbox \
    && mkdir /source && chmod 755 /source \
    && rm -rf /usr/local/lib/node_modules /opt/yarn-* \
    && rm -f /usr/local/bin/npm /usr/local/bin/npx /usr/local/bin/yarn /usr/local/bin/yarnpkg \
        /usr/local/bin/corepack /usr/local/bin/docker-entrypoint.sh
USER 65532:65532
WORKDIR /tmp
ENTRYPOINT []
CMD ["node", "--version"]
