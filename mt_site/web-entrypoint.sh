#!/bin/sh


. /code/venv/bin/activate

cd /code || return

echo $PATH

python manage.py load_tenant_config -f tenant_config.dev.json --include-tenant-metadata --flush-all
python manage.py migrate_all

echo 'yes' | python manage.py collectstatic

gunicorn -c gunicorn.conf.py mt_site.wsgi:application