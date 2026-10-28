#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate
python manage.py seed_data
python manage.py seed_kredensial_master
python manage.py seed_kredensial_accounts
python manage.py sync_nakes_kredensial
