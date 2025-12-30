#!/bin/sh

if [ "$DATABASE" = "postgres" ]
then
    echo "Czekam na bazę danych..."
    while ! nc -z $POSTGRES_HOST $POSTGRES_PORT; do
      sleep 0.5
    done
    echo "Baza danych gotowa!"
fi

# Automatyczne migracje (skoro baza jest czysta, to się przyda)
echo "Uruchamiam migracje..."
python manage.py migrate

# Opcjonalnie: Ładowanie fixture'ów lub tworzenie superusera (można to też zrobić ręcznie później)
# python manage.py loaddata initial_data.json

exec "$@"
