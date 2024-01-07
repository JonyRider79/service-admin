FROM python:3.12.1-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY ./main.py /app
EXPOSE 8000
CMD ["uvicorn", "--host", "0.0.0.0", "main:app"]
