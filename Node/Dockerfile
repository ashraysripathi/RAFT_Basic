FROM python:3.7-alpine3.14

COPY . .
RUN  pip3 install -r requirements.txt
EXPOSE 5555
ENTRYPOINT ["python", "-u", "server.py"]
