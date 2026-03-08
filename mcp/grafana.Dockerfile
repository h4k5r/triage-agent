FROM python:3.11-slim

WORKDIR /app

# Install the MCP server
RUN pip install --no-cache-dir grafana-mcp-server

# The command to run the server
# Note: Arguments like --url will be passed in via the Deployment's command or args
ENTRYPOINT ["grafana-mcp-server"]
