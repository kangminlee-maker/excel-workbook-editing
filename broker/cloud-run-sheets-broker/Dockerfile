FROM python:3.12-slim

WORKDIR /app
COPY src /app/src
ENV PYTHONPATH=/app/src
ENV PORT=8080

CMD ["python", "-m", "server"]
