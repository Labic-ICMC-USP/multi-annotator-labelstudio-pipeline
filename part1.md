# Tutorial — Multi-Annotator NER Pipeline with Label Studio Community Edition

## Part 1 — Installing Label Studio with Docker and PostgreSQL

This part shows how to install Label Studio Community Edition using Docker and PostgreSQL. This setup is more appropriate than SQLite for multi-user annotation because PostgreSQL is better suited for concurrent access and persistent storage. Label Studio’s official installation guide documents Docker-based installation and PostgreSQL support.

## Why use PostgreSQL

SQLite is acceptable for local testing, but PostgreSQL is a better choice for shared annotation environments because it handles concurrent access more reliably and is easier to maintain in larger projects. Label Studio’s installation documentation lists PostgreSQL as a supported database backend for self-hosted deployments.

## Prerequisites

Before starting, make sure the machine has:

* Docker installed
* Docker Compose available through `docker compose`

Docker’s official documentation explains how to install Docker Engine and use Compose as the standard way to run multi-container applications.

## Step 1 — Create the working directory

Create a directory for the deployment and enter it:

```bash
mkdir labelstudio-setup
cd labelstudio-setup
```

## Step 2 — Create the Docker Compose file

Create a file named `docker-compose.yml` with the following content:

```yaml
version: "3.9"

services:
  postgres:
    image: postgres:16
    container_name: labelstudio_postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: labelstudio
      POSTGRES_USER: labelstudio
      POSTGRES_PASSWORD: change_this_password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  labelstudio:
    image: heartexlabs/label-studio:latest
    container_name: labelstudio_app
    restart: unless-stopped
    depends_on:
      - postgres
    ports:
      - "8080:8080"
    environment:
      DJANGO_DB: default
      POSTGRE_NAME: labelstudio
      POSTGRE_USER: labelstudio
      POSTGRE_PASSWORD: change_this_password
      POSTGRE_HOST: postgres
      POSTGRE_PORT: 5432
    volumes:
      - labelstudio_data:/label-studio/data

volumes:
  postgres_data:
  labelstudio_data:
```

This configuration creates two containers:

* a PostgreSQL database container
* a Label Studio application container

It also defines persistent Docker volumes so that database contents and Label Studio files remain available after restarts. Docker’s documentation explains this persistent volume behavior, and Label Studio’s installation guide documents the Docker deployment pattern.

## Step 3 — Start the services

Run:

```bash
docker compose up -d
```

Then verify that the containers are running:

```bash
docker ps
```

You should see both:

* `labelstudio_postgres`
* `labelstudio_app`

## Step 4 — Open Label Studio in the browser

Open:

```text
http://localhost:8080
```

At first access, create the initial administrator account. This first account will be used to create projects, manage users, and generate an API token for later automation tasks. 
We recommend to generate Legacy Token from Label Studio web interface to use into importation python script.
Label Studio’s documentation describes the first-user and signup flow for self-hosted instances.

## Step 5 — Generate an API token

After logging in, open the account settings and generate a personal access token. This token will be used later to:

* create users by API
* create projects by API
* import tasks
* export annotations

Label Studio’s API documentation uses token-based authentication for these operations.

## Step 6 — Confirm data persistence

Stop the environment:

```bash
docker compose down
```

Start it again:

```bash
docker compose up -d
```

If your account and projects are still there after restart, persistent storage is working correctly. Docker volumes are designed for exactly this purpose.

## Recommended next improvements

For a more robust deployment, you should later add:

* Nginx as a reverse proxy
* HTTPS
* regular PostgreSQL backups
* a fixed Label Studio image version instead of `latest`

Using a pinned image version is generally safer for reproducibility and operational stability, and Docker recommends explicit image tagging for controlled deployments.

## Summary

At this point, the environment includes:

* Label Studio Community Edition running in Docker
* PostgreSQL as the backend database
* persistent volumes for data storage
* a browser-accessible annotation server on port 8080

This is a solid base for a multi-annotator workflow.

In Part 2, the next step is to create a NER project and define the labeling configuration.
