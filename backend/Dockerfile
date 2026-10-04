FROM python:3.12-slim
WORKDIR /srv/silong
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend backend
COPY config config
COPY scripts scripts
COPY frontend/public/data frontend/public/data
RUN python scripts/train_models.py
ENV PYTHONPATH=/srv/silong/backend
EXPOSE 8000
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
