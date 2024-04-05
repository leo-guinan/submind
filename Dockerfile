#Create a python dockerfile that can create the poetry environment
# and install the dependencies
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /usr/src/app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libsqlite3-mod-spatialite \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Upgrade dbs to the latest version
# Note: You may need to find the appropriate way to upgrade SQLite3 for your base image
RUN apt-get update \
    && apt-get install -y sqlite3  postgresql-client \
    && sqlite3 --version

RUN pip install poetry

COPY pyproject.toml poetry.lock* ./

# Install project dependencies via Poetry
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Copy the project files to the container
COPY . .

# The command to run the application
CMD ["python", "main.py"]