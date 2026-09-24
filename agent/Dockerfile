FROM ghcr.io/astral-sh/uv:python3.12-alpine

# Set the working directory
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy project files
COPY pyproject.toml uv.lock ./

RUN uv sync --no-install-project

# Copy the rest of the application
COPY . .

# Install the project
RUN uv sync

# Expose the FastAPI port
EXPOSE 8000

# Run the agent
CMD ["uv", "run", "main.py"]
