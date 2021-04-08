#!/bin/sh

. /code/venv/bin/activate

cd /code || return

echo $PATH

celery -A mt_site worker -l INFO