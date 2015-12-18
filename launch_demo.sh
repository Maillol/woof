#!/bin/bash

cd demo
export PYTHONPATH=$PYTHONPATH:$(dirname $PWD)
python3 -m msf createdb demo.controllers

echo "Start server"
gunicorn wsgi -D -p gunicorn.pid
sleep 1

echo -e "Send POST request..."
curl -H "Content-Type: application/json" -X POST http://127.0.0.1:8000/api/hotels -d '{"name": "Le Negresco", "address": "Promenade des Anglais - Nice"}'

echo -e "\nSend GET request..."
curl -H "Content-Type: application/json" -X GET http://127.0.0.1:8000/api/hotels

echo -e "\nStop server"
kill $(cat gunicorn.pid)
rm gunicorn.pid
rm demo.db
cd -
