#!/bin/bash
set -e

echo "🚀 Starting ERPMax Orchestrator..."

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL..."
while ! nc -z $POSTGRES_HOST $POSTGRES_PORT; do
  sleep 0.5
done
echo "✅ PostgreSQL is ready!"

# Run migrations
if [ "$RUN_MIGRATIONS" = "true" ]; then
  echo "🔄 Running database migrations..."
  alembic upgrade head
  echo "✅ Migrations completed!"
fi

# Start the application
echo "🎯 Starting application..."
exec "$@"
