# Pegasus production deployment

Prepare a Linux VPS with Docker Compose. Copy .env.production.example to .env.production, set a strong password and final HTTPS URL, then run:

    docker compose --env-file .env.production -f docker-compose.production.yml up -d --build

Keep PostgreSQL, Redis and API private. Put an HTTPS reverse proxy in front of web port 3000.