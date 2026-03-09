FROM node:20-slim

WORKDIR /app

# Install the MCP server and proxy globally
RUN npm install -g @modelcontextprotocol/server-github mcp-proxy

# Set the proxy port to match the Kubernetes Service
ENV PORT=8080
ENV TRANSPORT=sse

# The command to run the proxy server, which wraps the actual server
ENTRYPOINT ["mcp-proxy", "--server", "sse", "--port", "8080", "--", "mcp-server-github"]
