# Dependency Image
FROM accurics/terrascan:1.3.1 as terrascan

# Base Image
FROM alpine:3.13.1

RUN apk add --update --no-cache bash=5.1.0-r0 \
    ca-certificates=20191127-r5 curl=7.76.1-r0 \
    git=2.30.2-r0 python3=3.8.8-r0 py3-pip=20.3.4-r0 && \
    rm -rf /var/cache/apk/*

RUN pip3 install --no-cache-dir GitPython==3.1.14

# Install Terrascan
ENV PATH="/usr/local/bin/:${PATH}"
COPY --from=terrascan /go/bin/terrascan /usr/local/bin/
RUN /usr/local/bin/terrascan init

COPY terragrunt_action.py /terragrunt_action.py

ENTRYPOINT ["/terragrunt_action.py"]
