FROM python:3.14-slim

# keeps stdout/stderr flowing immediately
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install Python dependencies system-wide without creating a virtualenv
RUN pip install --no-cache-dir pipenv
COPY Pipfile Pipfile.lock ./
RUN pipenv install --system --deploy

# Copy the rest of the application code
COPY . .

EXPOSE 8000

RUN chmod +x entrypoint.sh
ENTRYPOINT ["./entrypoint.sh"]