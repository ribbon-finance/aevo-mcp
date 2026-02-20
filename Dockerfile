FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN python -m pip install --no-cache-dir --upgrade pip setuptools

COPY pyproject.toml ./
RUN pip install --no-cache-dir .

COPY src ./src
COPY README.md ./README.md

EXPOSE 8080

ENV AEVO_MCP_HOST=0.0.0.0 \
    AEVO_MCP_PORT=8080 \
    AEVO_MCP_PATH=/mcp \
    AEVO_MCP_TRANSPORT=streamable-http

CMD ["aevo-mcp", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8080", "--path", "/mcp"]
