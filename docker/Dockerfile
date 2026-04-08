FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    npm \
    libxml2-dev libxslt1-dev cmake libyaml-dev libclang-dev llvm-dev libglib2.0-dev libjson-glib-dev flex \
    && rm -rf /var/lib/apt/lists/*
    
RUN python3 -m pip install --no-cache-dir hotdoc

WORKDIR /docs
ENTRYPOINT ["hotdoc"]

# Default to showing help if no arguments are provided
CMD ["--help"]
