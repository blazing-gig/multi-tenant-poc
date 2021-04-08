import unittest

from django.test.runner import DiscoverRunner

from tenant_router.context_decorators import tenant_context_bind
from tenant_router.managers import tenant_context_manager
from tenant_router.orm_backends.utils import construct_conn_alias


class TenantAwareTestRunner(DiscoverRunner):
    manager = None

    @classmethod
    def set_manager(cls, manager):
        cls.manager = manager

    def _expand_template_alias_to_all_tenants(self, template_alias):
        return {
            construct_conn_alias(
                tenant_alias=tenant_context.alias,
                orm_key=self.manager.ORM_KEY,
                template_alias=template_alias
            )
            for tenant_context in tenant_context_manager.all()
        }

    def _get_normalized_conn_alias(self, alias):
        if alias in self.manager.template_aliases:
            return self._expand_template_alias_to_all_tenants(
                alias
            )
        else:
            return {alias}

    def _normalize_aliases(self, aliases):
        normalized_aliases = set()

        for alias in aliases:
            normalized_alias = self._get_normalized_conn_alias(alias)
            normalized_aliases.update(normalized_alias)

        return normalized_aliases

    def _fetch_db_aliases(self, suite, state):
        if not state:
            state['test_classes'] = set()

        final_conn_aliases = set()
        for test in suite:

            # if test is an instance of `unittest.TestCase` then pull
            # out the 'databases' attribute present at the class level and
            # normalize it.
            if isinstance(test, unittest.TestCase):
                conn_aliases = set()

                # normalize 'databases' only if the class hasn't been
                # encountered previously.
                if test.__class__ not in state['test_classes']:
                    db_aliases = getattr(test, 'databases', None)

                    if db_aliases:

                        if db_aliases == '__all__':
                            test.__class__.databases = \
                                conn_aliases = self.manager.conn_aliases
                        else:
                            conn_aliases = self._normalize_aliases(
                                db_aliases
                            )
                            test.__class__.databases = conn_aliases

                        state['test_classes'].add(test.__class__)

            else:
                conn_aliases = self._fetch_db_aliases(
                    test,
                    state=state
                )

            final_conn_aliases.update(conn_aliases)

        return final_conn_aliases

    def get_databases(self, *args, **kwargs):
        suite = args[0]
        final_conn_aliases = self._fetch_db_aliases(
            suite, state=dict()
        )
        return final_conn_aliases

    def run_tests(self, *args, **kwargs):
        with tenant_context_bind(
                tenant_context_manager.get_random_context()
        ):
            return super().run_tests(*args, **kwargs)
