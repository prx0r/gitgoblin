FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY gitgoblin ./gitgoblin
COPY configs ./configs
RUN pip install --no-cache-dir .
EXPOSE 8787
CMD ["gitgoblin", "serve", "--host", "0.0.0.0", "--port", "8787"]
