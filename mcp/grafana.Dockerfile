FROM python:3.11-slim

WORKDIR /app

# Install the MCP server
RUN pip install --no-cache-dir mcp-grafana

# Set the HTTP port
ENV PORT=8080

# The command to run the server
ENTRYPOINT ["python", "-m", "mcp_grafana"]
