FROM python:3.11-slim as django-base

WORKDIR /app

COPY requirements.txt requirements.txt
RUN python -m pip install --no-cache-dir -r requirements.txt 

RUN adduser --disabled-password --gecos '' user && mkdir /app/logs && chown -R user:user /app/

FROM django-base as django-server

# USER user
COPY . .

# CMD ["python", "-m" ,"debugpy", "--listen", "0.0.0.0:3000", "-m", "app"]
CMD [ "./docker-entrypoint.sh" ]