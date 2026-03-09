FROM node:20-slim

WORKDIR /app

# Install kubectl to support the MCP server's underlying CLI commands
RUN apt-get update && apt-get install -y curl && \
    curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && \
    install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl && \
    rm -rf /var/lib/apt/lists/*

# Install the community MCP server and SSE proxy globally
RUN npm install -g mcp-server-kubernetes mcp-proxy

# Set the HTTP port
ENV PORT=8080

# The command to run the proxy
ENTRYPOINT ["mcp-proxy", "mcp-server-kubernetes"]
