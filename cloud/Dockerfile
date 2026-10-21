FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir tzdata pywebpush
COPY . /app
ENV PYTHONUNBUFFERED=1
CMD ["python", "app.py"]
