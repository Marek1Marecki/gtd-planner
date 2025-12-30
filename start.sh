#!/bin/bash
# Przejdź do katalogu, w którym znajduje się ten skrypt
cd "$(dirname "$0")"

echo "🚀 Uruchamiam projekt w: $(pwd)"

# Sprawdź, czy Docker działa
if ! docker info > /dev/null 2>&1; then
  echo "❌ Błąd: Docker nie jest uruchomiony."
  exit 1
fi

# Uruchom kontenery w tle (-d) i pokaż logi
docker compose up -d
echo "✅ Kontenery uruchomione w tle."
echo "📜 Wyświetlam logi (naciśnij Ctrl+C aby wyjść z podglądu logów, serwer będzie działał dalej):"
docker compose logs -f web
