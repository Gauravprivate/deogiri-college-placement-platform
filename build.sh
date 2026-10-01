#!/usr/bin/env bash

python manage.py migrate
python seed_render.py
python manage.py collectstatic --noinput