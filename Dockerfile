FROM python:3.12-slim
ADD requirements.txt /tmp
RUN pip install -r /tmp/requirements.txt
WORKDIR /app
ADD Friday.py /app
ADD db.py /app
ENTRYPOINT python /app/Friday.py