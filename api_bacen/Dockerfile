FROM python:3.9-slim
WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --upgrade pip setuptools wheel
RUN pip install -r requirements.txt
RUN pip install PyJWT

COPY main.py .
EXPOSE 8008
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8008"]