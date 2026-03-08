FROM node:20-slim

WORKDIR /app

# Install the MCP server globally
RUN npm install -g @modelcontextprotocol/server-github

# The command to run the server
ENTRYPOINT ["mcp-server-github"]
