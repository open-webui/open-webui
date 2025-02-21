# source version
ARG version
# env, dev, test, prod
ARG env
# harbor host
ARG harbor

# step1 build
FROM ${harbor}/cicd/node:20 as builder
WORKDIR /app

COPY package.json /app/package.json
COPY package-lock.json /app/package-lock.json
COPY Makefile /app/Makefile
RUN make install-deps

ARG version
ARG env
COPY . /app
RUN make pack ENV=${env} VERSION=${version}

# step2 run
FROM ${harbor}/cicd/static_nginx_base:v1.2.0
ARG env
COPY --from=builder /app/package /app
COPY deploy/gpt-oi-web/${env}/entrypoint.sh /
RUN chmod +x /entrypoint.sh
ENTRYPOINT /bin/sh -c /entrypoint.sh