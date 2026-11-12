#!/usr/bin/env bash
# Render build step: install, collect static files, migrate, load demo data, create the sign-in account.
set -o errexit
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput
python manage.py seed_demo
python manage.py ensure_demo_user
