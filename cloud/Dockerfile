FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir tzdata pywebpush
COPY app.py describe.py ./
COPY logos ./logos
ENV PYTHONUNBUFFERED=1
CMD ["python", "app.py"]
