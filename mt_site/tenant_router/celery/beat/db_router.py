import inspect

from django_celery_beat import models
from django.db.models import Model

from tenant_router.celery.utils import CELERY_BEAT_DB_ALIAS, CELERY_BEAT_APP_LABEL


class CeleryBeatRouter:

    def __init__(self):
        self._celery_beat_models = self._get_celery_beat_models()

    def _get_celery_beat_models(self):
        def filter(obj):
            return inspect.isclass(obj) and issubclass(obj, Model)

        return {
            klass for klass_name, klass in inspect.getmembers(
                models, filter
            )
        }

    def db_for_read(self, model, **hints):
        if model in self._celery_beat_models:
            return CELERY_BEAT_DB_ALIAS

        return None

    def db_for_write(self, model, **hints):
        if model in self._celery_beat_models:
            return CELERY_BEAT_DB_ALIAS

        return None

    def allow_relation(self, *args, **kwargs):
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if db == CELERY_BEAT_DB_ALIAS:
            if app_label == CELERY_BEAT_APP_LABEL:
                return True
            else:
                return False

        return None
