#!/bin/bash
# Skript pro restart serveru – zastaví proces na portu 3333 a znovu spustí server

cd "$(dirname "$0")"

PORT=3333
echo "Zastavuji proces na portu $PORT..."
if command -v lsof >/dev/null 2>&1; then
  PID=$(lsof -ti :$PORT 2>/dev/null)
  if [ -n "$PID" ]; then
    kill $PID 2>/dev/null || true
    sleep 2
    # pokud stále běží, force kill
    lsof -ti :$PORT 2>/dev/null | xargs kill -9 2>/dev/null || true
  fi
fi
pkill -f "node.*server.js" 2>/dev/null || true
sleep 1

echo "Spouštím server na http://localhost:$PORT ..."
npm start
