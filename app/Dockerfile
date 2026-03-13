FROM python:3.10-slim

WORKDIR /workspace

COPY requirements.txt /workspace/requirements.txt
RUN pip install --no-cache-dir -r /workspace/requirements.txt

COPY app /workspace/app
COPY src /workspace/src
COPY data /workspace/data

ENV PYTHONPATH=/workspace

WORKDIR /workspace/app

EXPOSE 8501
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
