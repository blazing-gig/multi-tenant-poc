# About

This project is a PoC of how a pip installable re-usable Django app can be built in order to convert a conventionally built single-tenant Django application into its multi-tenant version with minimal/no code change.

Traditionally SAAS platforms have adopted multiple approaches to achieving multi-tenancy. The two most common and widely used are the following:

1. Isolated DB approach -> Each tenant stores its data in a separate database.
2. Shared DB approach -> Data from multiple tenants are collocated in the same database but every row relates to a specific tenant by means of a database relation constraint.

This project adopts the first (isolated DB) approach due to the following reasons:

1. Typically SAAS platforms have an SLA stating that every tenant's data has to be complete isolated from one another so as to avoid potential data leaks or data overlap.
2. If the shared DB approach is chosen, it would entail both code change as well as DB schema changes/migrations etc., which can be time consuming for already running live applications to accomodate.
3. Most of the tools around DB management (like DB dump/restore, monitoring etc.,) are built to operate at the database level. If the shared DB approach is chosen, then these tools would either become obsolete or would have to be used with modifications made on a case-to-case basis and ends up becoming a bottle-neck for the migration process.
4. Currently there is no general purpose package/library which is battle-tested and production ready that can be plugged into existing single-tenant applications to make them multi-tenant by following this approach. ([django-db-multitenant](https://github.com/mik3y/django-db-multitenant) has been deemed experimental by the authors)

The following architecture diagram explains better as to what the package/library achieves:

![Multi-tenant architecture diagram](img/quickstart_mt_arch.png)

> **NOTE**: The term *package/library* used above refers to the [tenant_router](mt_site/tenant_router) Django app which is currently a part of the web appication made for demonstrating the PoC. However, it has been built in such a way that it can be abstracted out into a re-usable pip installable app that can be plugged into any existing Django web application to solve the multi-tenancy problem.


# How does it work?

The library essentially solves two major problems:

1. **Routing DB queries to appropriate tenant DBs' at runtime**: This is one of the core components of the library. This is achieved by creating a connection management and routing layer on top of DB wrapper/connector libraries (like ORMs') thereby making the solution database agnostic. 

2. **Real time propagation of tenant configuration changes**: To elaborate on the problem, any configuration change (like DB url, cache url etc.,) that happens when an Add tenant/Update tenant/Delete tenant takes place, has to be communicated to and processed by all running instances of the app server at any given time. This is solved by means of a niche Pub/Sub mechanism in place which we term as ***reactive configuration***.

Apart from the above mentioned solutions, the library also offers out-of-the-box support for various other components that a typical Django web app would use. These include:

1. Caches
2. Database migrations
3. Celery
4. Shell operations
5. Unit testing methods in this new paradigm
6. Management commands (like migrate, dumpdata, loaddata etc.,)

> **NOTE**: Of the components mentioned above, the code in this repo contains support for only a few of them as this is just for demonstration pruposes. However, ideas by which support can be extended for the other components will be discussed in the conference.

# Running the demo app

## Pre-requisites

The demo app comes in a completely dockerised setup. In order to launch it, it's mandatory to
have [Docker](https://www.docker.com/get-started) and 
[docker-compose](https://docs.docker.com/compose/install/) installed and available as part of
the system `PATH`.

Before launching the app, in order to verify its multi-tenant behaviour, a couple of host
entries namely `tenant-1.test.com` and `tenant-2.test.com` must be added to the namespace
resolver of your machine. Thus when the browser points to one of these hosts, the demo
app's backend would be able to route requests to the appropriate database. 

For Linux and MacOS users, please add the following entries to the `/etc/hosts` file as below:

```
##
# Host Database
#
# localhost is used to configure the loopback interface
# when the system is booting.  Do not change this entry.
##
...
127.0.0.1 tenant-1.test.com
127.0.0.1 tenant-2.test.com
...
# End of section
```

> **NOTE**: You might need to ensure that the current user has `sudo` privileges in order to edit the
`/etc/hosts` file.


## Launch

To launch the app, enter the following commands:

```shell
$ cd ~/multi-tenant-poc
$ docker-compose build
$ docker-compose up -d
```

To test things out, try the following:

1.  Open your browser and point it to `tenant-1.test.com:9500`. You should see the
    following image:
    
    ![tenant 1 screen](img/tenant_1_landing_screen.png)

2.  Now, point the browser to `tenant-2.test.com:9500`. You should see the following image.
    
    ![tenant 2 screen](img/tenant_2_landing_screen.png)
    
    You can see that, in the above image, the data for the **Hospitals** tab is different
    compared to the data that was displayed for `tenant-1.test.com`. This confirms that requests
    are being routed to different databases based on the domain name.
    
3.  As you can see, in both the above screens, the **Patients** tab is empty. Let's try adding one. 
    Click on the **Add Patient** button and fill up the form with the required details and submit
    it. You should see the following screen once submitted:
    
    ![Add Patient Dialog](img/patient_add_success.png)
    
    By now, you would have noticed the small spinner near the **Add Patient** button. Every time the
    spinner completes one full rotation, the **Patients** tab is refreshed. 
    
    The reason for doing this is that the Add Patient HTTP endpoint does not immediately add the
    new patient to the database but rather delegates this responsibility to a 
    ***celery task***. Hence, the UI would be able to reflect the latest changes only after the
    celery task completes its execution.
    
    The aim of the above implementation is to illustrate that every *celery task* that the app
    has, when invoked, is bound to a specific tenant's context without any code changes. 
    
    > **INFO**: Verify the above statement by pointing your browser to `tenant-1.test.com:9500`. You 
    would find that the **Patients** tab is still empty.
    

# Reference

## Configuration

The following configuration options are available and will have to be provided in the `settings.py` 
module.

### **```CONFIG STORE```**
*Required*. Type: `dict`

This setting holds the configuration for the KV(key/value) store that would be looked up at
boot time to pull the necessary configuration and bootstrap various components of this package
(like ORM managers etc.,).

Any suitable cache backend compatible with Django's `CACHES` can be used to provide the required
functionality. 

Below is an example configuration:

```python
# settings.py
...
CACHES = {
    "tenant_router_config_store": {
        "BACKEND": "django_redis.cache.RedisCache",
        "TIMEOUT": None,
        "LOCATION": "redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}".format(
            REDIS_HOST='your_redis_host',
            REDIS_PORT='your_redis_port',
            REDIS_DB='your_db_index'
        ),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SERIALIZER": "django_redis.serializers.json.JSONSerializer"
        }
    }
}
...
```

> **IMPORTANT**:
    Django, by default, associates a timeout (ttl) with all keys stored in a given cache. Since we expect the data
    in the config store to be persistent (i.e no timeout), the `TIMEOUT` parameter has to be explicitly
    set to `None`.

> **NOTE**:
    The `tenant_router_config_store` is a reserved special key which would be used internally by the 
    library for identifying the cache containing the tenant configuration. If it conflicts with an 
    already existing key, the conflicting key (specified by the user) will have to be changed.  

For details about the schema of this configuration, [click here](#configuration-file). 


### ```TENANT_ROUTER_SERVICE_NAME``` (mandatory)

The service name identifier that would be used for construction/de-construction of the keys configured in the
KV store.

Example:
```python
...
TENANT_ROUTER_SERVICE_NAME = 'some_string'
...
```


### ```TENANT_ROUTER_ORM_SETTINGS``` (mandatory)

A mapping of orm identifier to orm configuration. At a higher level, this orm configuration, behind the scenes,
is used for managing connections and routing to the correct database based on the tenant context set by the
middleware for a particular request/response cycle.

An application could potentially use multiple ORM libraries like the Django ORM, PyModm/MongoEngine (for MongoDB)
etc., So each of these ORMs' should register themselves as part of this configuration to define their respective
```manager``` classes and provide a ```settings``` key from where they would pick up
template configurations which would get replicated across tenants.

The package currently ships with a ```manager``` class for Django ORM. 

Example:
```python
import os

# assume that in the single-tenant application built, 
# the following configuration was provided.
DATABASES = {
    "default": {
        "NAME": os.environ["PG_DATABASE"],
        "USER": os.environ.get("PG_USER"),
        "PASSWORD": os.environ.get("PG_PASSWORD"),
        "HOST": os.environ["PG_HOST"],
        "PORT": os.environ["PG_PORT"],
    }
}
...
# The most basic form of this setting is as follows:
TENANT_ROUTER_ORM_SETTINGS = {
    'django_orm': {
        'SETTINGS_KEY': 'DATABASES'
    }
}
...

# Also if the Django ORM is being used, make sure to configure the 
# DATABASE_ROUTERS setting as follows:
DATABASE_ROUTERS = ['tenant_router.orm_backends.django_orm.router.DjangoOrmRouter']

```

> Note that in the above example, `django_orm` is a reserved key since
> the package already has a manager defined for this.

If the application uses an ORM library which is not supported out of the box by this package, it
is possible to write a `manager` class for that ORM and set it up. Also if the default `manager`
provided doesn't account for a custom use-case, it can be overridden as well.

Example:

```python
...
TENANT_ROUTER_ORM_SETTINGS = {
    # overriding the default manager
    'django_orm': {
        'MANAGER': 'full_dotted_path_to_custom_manager_cls',
        'SETTINGS_KEY': 'some_key'
    },
    # providing a new manager for the mongoengine ORM library
    'mongoengine': {
        'MANAGER': 'full_dotted_path_to_custom_manager_cls',
        'SETTINGS_KEY': 'some_key'
    },
}
...
```

> If you'd like to implement a custom `manager` class, check out the 
> `tenant_router.orm_backends.base.manager` file for the interface required to be implemented.

### `TENANT_ROUTER_MIDDLEWARE_SETTINGS` (optional)

The middleware which is responsible for injecting the *tenant context* in every request can be
customized as follows:

- `WHITELIST_ROUTES` => A `set` of route identifiers for which the *tenant context need not be
  injected*. In other words, these routes by-pass the middleware. Each route identifier must take
  one of the following values:

    1. **View name** => Full dotted path to the view that should be whitelisted.
    2. **Route name** => The *route* part of the `path` instance in `urlpatterns`.
    3. **Url name** => The value given to the `name` parameter, if specified in the `path` instance.
       For *namespaced urls*, it would be of the form `namespace_identifier:url_name`.

  In order to resolve the request path into one of the above, the `django.urls.resolve` method
  is used internally. For more info about how this method behaves,
  [click here.](https://docs.djangoproject.com/en/2.2/ref/urlresolvers/#resolve)

Example:
```python
## urls.py
from django.urls import path, include
...
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/sample/', SampleView.as_view(), name='sample_view')
]

## settings.py

#### In order to whitelist `SampleView` from the above urls.py, any of the following approaches
#### would work fine.
...
TENANT_ROUTER_MIDDLEWARE_SETTINGS = {
    'WHITELIST_ROUTES': {
        # Full dotted path to view (or)
        'path.to.SampleView',
        # Route part of the `path` instance (or)
        'api/sample/',
        # Url name specified in the `path` instance
        'sample_view'
        # if namespaced, then the above becomes
        'sample_app:sample_view' 
        # where 'sample_app' is the namespace identifier 
    }
}
...
```

- `TENANT_ID_RESOLVER` => A `callable` which will be called with the
  [http request object](https://docs.djangoproject.com/en/2.2/ref/request-response/#httprequest-objects)
  in order to resolve the *tenant identifier*. This will subsequently be used to get the
  corresponding *tenant context* to be injected for that particular http request.


Example:
```python
## some_module.py
...
def resolve_tenant_id(request):
    # logic to resolve tenant id based on something in the 
    # request object.
    return 'tenant_identifier'

## settings.py
...
TENANT_ROUTER_MIDDLEWARE_SETTINGS = {
    'TENANT_ID_RESOLVER': 'path.to.some_module.resolve_tenant_id'
}
...
```

### ```TENANT_ROUTER_BOOTSTRAP_SETTINGS``` (optional)

There are a bunch of internal components in the package that get bootstrapped in a particular sequence when
Django fires the `ready` signal.

During this bootstrap phase, the application can potentially configure this setting with a sequence of
`callables` if there is some activity to be performed after the pre-defined sequence gets executed.

Example:
```python
...
TENANT_ROUTER_BOOTSTRAP_SETTINGS = [
    'callable_1', 
    'callable_2',
    ...
]
...
```

### ```TENANT_ROUTER_CACHE_SETTINGS``` (optional)

Since the concept of **template** and **reserved** aliases can be extended to `caches` as well, they
can be configured, as applicable, in the following way.

```python
# settings.py
...
TENANT_ROUTER_CACHE_SETTINGS = {
    'RESERVED_ALIASES': set(['some_alias', 'some_other_alias']) 
}
...
```

To get a detailed understanding of what this means, [click here](#caches)


## Configuration File

In order to load the metadata required by the library, a configuration file has to be created.
By convention, this file should be named `tenant_config.json` and should be present at the same
directory level as `settings.BASE_DIR`.

The configuration specified in this file is synced to the
[config store](#config-store) when the
`load_tenant_config` command is run. 

### Schema

### `mapping_metadata`
*Required*

This key is used for defining a one-to-one mapping of *deployment keys* to their corresponding
translation values.

### `tenant_config` 
*Optional*

This key contains tenant specific configuration like DB, cache etc.,
The schema definition for this key is as follows:

```json
{
    "tenant_config": {
        "tenant_identifier": {
            "service_identifier": {
                "orm_config": {
                    "orm_identifier": {
                        "template_alias": {... #db_config}
                    }
                },
                "cache_config": {
                    "template_alias": {
                        ... #cache_config
                    }            
                }  
            }
        }
    }
}
```

> **NOTE**:
The `service_identifier` key mentioned above should match the value provided for the 
`TENANT_ROUTER_SERVICE_NAME` setting as this is used for construction/de-construction of
keys stored in the KV store.


Lets take a look at a more concrete example:
```json
{
    "tenant-1.test.com": {
        "test_service": {
            "orm_config": {
                "django_orm": {
                    "default": {
                        "HOST": "...",
                        "NAME": "...",
                        "USER": "...",
                        "PASS": "...",
                        "PORT": "..."
                    }
                },
                "pymodm_orm": {
                    "default": {
                        "CONN_URL": "..."
                    }
                }
            },
            "cache_config": {
                "default": {
                    "LOCATION": "..."
                }
            }
        }
    },
    "tenant-2.test.com": {...}
}   
```

### Populating the KV store

In order to populate the KV store with the configuration in the above file, the 
`load_tenant_config` command has to be run with `manage.py`

```shell script
$ python manage.py load_tenant_config
```

To know more about specifying alternate file paths and other available options, run:

```shell script
$ python manage.py load_tenant_config --help
```

## DB Migrations

Typically a web app would need interact with one or more databases. Also, in a Django app, this interaction
typically happens through an ORM. Each ORM, depending on the databases' it supports, could define its own
migration strategy to apply data model changes.

Since this package could potentially interact with multiple ORMs' through their respective `manager` classes,
it becomes essential for the `manager` class to know the migration strategy that the particular ORM uses.

Also it could be that an ORM does not have a defined migration strategy out of the box, in which case the app
which uses that ORM would have to define one.

Among the ORM libraries that the package supports, only `django_orm` has a well defined migration
strategy. For the others, the app would have to implement a `migration_asst` class and register it with the
respective `manager` class.

### Running migrations
The below snippet should be invoked with `manage.py`

```shell script
$ python manage.py migrate_all
```

> **WARNING**: Running the `python manage.py migrate` sub-command **would no longer work** as
> this is tied to only the `django_orm`. Other ORMs' would get left out from the
> migration process.

To know more about this command and the available options, run:

```shell script
$ python manage.py migrate_all --help
```


### Defining a custom `MIGRATION_ASST` class

The below snippet illustrates how to write a custom `migration_asst` class and register
it with the respective orm `manager` class.

```python

## Example of a custom 'migration_asst' class
from tenant_router.orm_backends.base import BaseOrmMigrationAsst

class CustomMigrationAsst(BaseOrmMigrationAsst):
    
    def perform_migrate(self):         
        # Called by the 'manager' class internally when 
        # 'migrate_to_all' is called. Should implement the 
        # strategy for migrating to all databases supported 
        # by this ORM.
        pass


## Registering the class with a 'manager' in 'settings.py'
TENANT_ROUTER_ORM_SETTINGS = {
    'django_orm': {
        'MANAGER': 'tenant_router.orm_backends.django_orm.manager.DjangoOrmManager',
        'SETTINGS_KEY': 'DATABASES',
        'OPTIONS': {
            'MIGRATION_ASST': {
                # Mandatory
                'CLASS': 'path.to.CustomMigrationAsst',
                # Optional
                # Any additional kwargs to be passed to the class
                'OPTIONS': {}
            }
        }
    }
}
```

## Routers and routing strategies

Since the Django ORM supports routing to multiple databases at the ORM level using a concept called
***database routers***, there are a few scenarios to consider with respect to defining custom routers and the
different routing strategies that are possible.

A router in Django when implemented, is responsible for providing one or more of the following
functionalities:

- Provides a database for every write operation made via the ORM.
- Provides a database for every read operation made via the ORM.
- Tells whether relations between objects should be allowed or not.
- Tells which models should be migrated onto a particular database.


### Scenario 1: Single DB replicated across tenants

Consider the following example of a conventionally built single-tenant Django app.

```python
# settings.py file
import os

DATABASES = {
    "default": {
        "NAME": os.environ["PG_DATABASE"],
        "USER": os.environ.get("PG_USER"),
        "PASSWORD": os.environ.get("PG_PASSWORD"),
        "HOST": os.environ["PG_HOST"],
        "PORT": os.environ["PG_PORT"],
        "OPTIONS": {...}
    }
}

# KV store settings for the above template
{
    "some_tenant_a_prefix_default": {
        "NAME": "some_value",
        "USER": "some_value",
        "PASSWORD": "some_value",
        "HOST": "some_value",
        "PORT": "some_value",      
    },
    "some_tenant_b_prefix_default": {
        "NAME": "some_value",
        "USER": "some_value",
        "PASSWORD": "some_value",
        "HOST": "some_value",
        "PORT": "some_value",      
    }
}
```

From the above example, we infer that the `default` key in the `DATABASES` setting is actually a **template**
and the actual configuration for this template, for each tenant, is defined in the KV store.

Now for this scenario, the expected behavior of the router is as follows:

- All writes should be sent to the respective tenant's DB with alias of the form
  `some_tenant_prefix_default`.
- All reads should be sent to the respective tenant's DB with alias of the form
  `some_tenant_prefix_default`.
- All relations between objects should be allowed within a particular tenant's DB.
- All models present in the app should be migrated to all tenant DBs'.

The above behavior is *exactly* what the app will get when it plugs-in the `DjangoOrmRouter` class that ships
with the package.

```python
# settings.py

...
DATABASE_ROUTERS = ['tenant_router.orm_backends.django_orm.router.DjangoOrmRouter']
...
```


### Scenario 2: Central / Tenant-specific DBs

This is a typical scenario in a multi-tenant cloud environment wherein the web app
interacts with both a tenant-specific DB and a central DB, which is common across tenants. The diagram below
illustrates this case.

// diag goes here.

The configuration in `settings.py` could be as follows:
```python
import os
...

DATABASES = {
    # template alias
    "default": {
        "NAME": os.environ["PG_DATABASE"],
        "USER": os.environ.get("PG_USER"),
        "PASSWORD": os.environ.get("PG_PASSWORD"),
        "HOST": os.environ["PG_HOST"],
        "PORT": os.environ["PG_PORT"],
        "OPTIONS": {...}
    },
    # reserved key
    "central_db": {
        "NAME": os.environ["PG_DATABASE"],
        "USER": os.environ.get("PG_USER"),
        "PASSWORD": os.environ.get("PG_PASSWORD"),
        "HOST": os.environ["PG_HOST"],
        "PORT": os.environ["PG_PORT"],
        "OPTIONS": {...}
    }
}

# KV store settings for the above template
{
    "some_tenant_a_prefix_default": {
        "NAME": "some_value",
        "USER": "some_value",
        "PASSWORD": "some_value",
        "HOST": "some_value",
        "PORT": "some_value",      
    },
    "some_tenant_b_prefix_default": {
        "NAME": "some_value",
        "USER": "some_value",
        "PASSWORD": "some_value",
        "HOST": "some_value",
        "PORT": "some_value",      
    }
}
```

From the above example, we infer that the `default` key is treated as a **template alias** for which the
actual configuration comes from the KV store, for each tenant. However the `central_db` key is
treated as a **reserved alias** as its configuration comes from the `env`
and not the KV store since it remains the same across all tenants.


In such a case, the expected behavior of the router is as follows:

- All writes should be sent either to a tenant-specific DB or the central DB depending
  on some condition.
- All reads should be sent either to a tenant-specific DB or the central DB depending
  on some condition.
- Relations between objects should be allowed within the same DB (either tenant-specific / central)
- A migration strategy which decides whether a model should be migrated on to the central DB or
  tenant-specific DB.

In order to achieve the above, the following modifications should be made:

1. **Action**:
   Provide a router for each **reserved alias** defined and stack it on top of
   the `DjangoOrmRouter` class in the `DATABASE_ROUTERS` setting. <br>
   **Purpose**:
   Since all routers defined for each **reserved alias** would be consulted in order
   before falling back to the `DjangoOrmRouter`, it ensures that custom routing/migration logic
   for each reserved alias would be tried and executed before executing the routing/migration logic for
   template aliases.

2. **Action**:
   Provide keys which should be treated as **reserved aliases** to the `manager` class. <br>
   **Purpose**:
   This helps in isolating the **template aliases** from the reserved ones so as to power
   up a few public APIs of the `manager` class and also for other internal purposes.

3. **Action**:
   A custom migration strategy callable should be plugged into the `DjangoOrmRouter` class.
   This would be called from within the `allow_migrate` method whose return value
   will be the value that this callable returns. <br>
   **Purpose**:
   This callable would decide whether a particular model gets migrated onto DBs'
   defined as part of the **template aliases**.


```python
# custom router for the 'central_db' reserved alias
class CustomRouter:

    def db_for_read(self, model, **hints):
        if some_condition:
            return "central_db"
        return None

    def db_for_write(self, model, **hints):
        if some_condition:
            return "central_db"

        return None

    def allow_relation(self, *args, **kwargs):
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if some_condition:
            return True
        else:
            return False
        return None


# sample migrate_strategy_callable
def migrate_strategy(
        router, db, app_label, model_name=None, **hints
):
    if some_condition:
        return True
    else:
        return False

    return None


# modified settings
DATABASE_ROUTERS = [
    'path.to.CustomRouter',
    'tenant_router.orm_backends.django_orm.router.DjangoOrmRouter'
]

TENANT_ROUTER_ORM_SETTINGS = {
    'django_orm': {
        'MANAGER': 'tenant_router.orm_backends.django_orm.manager.DjangoOrmManager',
        'SETTINGS_KEY': 'DATABASES',
        'OPTIONS': {
            # marking the 'central_db' key as a reserved alias
            'RESERVED_CONN_ALIASES': {'central_db'},
            # plugging in the callable which defines the custom migrate strategy
            'ROUTER_OPTS': {
                'MIGRATE_STRATEGY': 'path.to.migrate_strategy_callable'
            }
        }
    }
}
```

## Shell

Since all DB queries made via the ORM, would now need to be
bound to a tenant context, by default, **any query run from within the shell would fail**.

In order to fix this, some tenant context has to be set explicitly as follows:

```shell script
$ python manage.py shell
>>> from tenant_router.managers.task_local import tls_tenant_manager
>>> from tenant_router.managers import tenant_context_manager
>>> from tenant_router.context_decorators import tenant_context_bind
>>> tls_tenant_manager.push_tenant_context(
... tenant_context_manager.get_by_id('some_tenant_id'))
>>> ...some queries with some_tenant_id as context...
>>> tls_tenant_manager.pop_tenant_context()
>>> with tenant_context_bind('some_other_tenant_id'):
>>>     ... some more queries with some_other_tenant_id as context
>>> quit()
```

> **WARNING**: For Django ORM, if **reserved aliases** have been defined, then it is possible
> to execute queries pertaining to the models which are linked to those aliases
> without setting a tenant context but this is highly ***not recommended*** as this
> could cause unnecessary confusion around why a few queries would fail but others would
> succeed.

## Caches

Django provides out-of-the-box support for configuring and using various `cache` systems with the
web server. Typically, for a single-tenant web app, there could be zero or more caches
configured as part of the `CACHES` dictionary.

Example:
```python
# settings.py

...
CACHES = {
    "default": {...},
    "alias-1": {...}
}
...
```

Now in the context of a multi-tenant web app, the following scenarios are possible:

1. All caches defined are *tenant-specific* and located in respective tenant environments.
2. Some caches could be *tenant-specific* while others could be *centrally* located.

Combining both the above scenarios, the configuration above would have to be expanded as follows:
```python
# settings.py
# assume that 'tenant-1' and 'tenant-2' are the respective tenant ids.

CACHES = {
    # 'default' cache is centrally located
    "default": {...},
    
    # 'alias-1' cache is located in
    # the tenant-specific environment. 
    "tenant-1-alias-1": {...},
    "tenant-2-alias-1": {...}
}
``` 

As a consequence of the above configuration expansion, the following problems occur:

1. It is not possible to hard-code the configurations for the respective tenants as mentioned above,
   as tenant configurations can be added/changed dynamically and so they will have to be updated at
   runtime without a server restart.
2. In an already existing code base, any access to a particular cache would have been done as
   follows:
```python
...
from django.core.cache import caches
cache = caches['default']
# some cache ops to follow
...
```
All places where access to cache has been made in the above way has to be refactored to include the
`tenant_id` prefix as applicable. For eg:
```python
...
from django.core.cache import caches

# The following line 
cache = caches['alias-1']

# would have to be refactored into
cache = caches['tenant-1-alias-1']
...
``` 
Also since such access could be made from a `view`, the `tenant_id` prefix would have to be picked
up dynamically as well from the current request context.

Both the above problems have been solved auto-magically by the library via a monkey patch that 
runs when the app bootstraps. 

> **IMPORTANT**: However, it is highly recommended that developers create a singleton 
instance of the `tenant_router.cache.patch.TenantAwareCacheHandler` class in code and refactor 
imports from `from djang.core.cache import caches` to `path.to.tenant_aware_cache_handler_instance`

In order to discern which aliases are to be treated as **reserved**, the 
`TENANT_ROUTER_CACHE_SETTINGS` has to be configured. For details about how to 
configure this setting, [click here](#tenant_router_cache_settings-optional)

## Unit tests

### Django ORM

Since the web app is now capable of interacting with multiple DBs', the following guidelines have been laid
down by Django in this context, which have to be understood first to proceed further.

- [Multi-DB testing scenarios](https://docs.djangoproject.com/en/2.2/topics/testing/advanced/#tests-and-multiple-databases)
- [Multi-DB support for tests](https://docs.djangoproject.com/en/2.2/topics/testing/tools/#multi-database-support)

### Caveat
As the first point above highlights, in order to control the creation order of databases, a `DEPENDENCIES` key
could be specified for each DB configuration. By default, Django assumes that all DBs' depend on the
`default` DB unless the `DEPENDENCIES` key is explicitly set, and so will create the `default` database
first. Django also implicitly assumes that the `default` database has no dependencies.

However since the `DATABASES` configuration could now potentially contain a mix of **reserved aliases** and
**template aliases**, the default behavior of Django would break if the `default` DB is marked as a
*template alias* because when Django tries to create it, it would error out since the . In order to prevent this from happening, it
is **mandatory to set the `DEPENDENCIES` key explicitly in all DB configurations** according to the
following rules based on alias type:

1. **Template alias**: The value should either be an empty list or can have **only
   reserved aliases** <br> in it.
2. **Reserved alias**: The value should either be an empty list or can have other
   reserved aliases <br> in it.

Below is an illustration of the above mentioned points:

```python
# settings.py
...
DATABASES = {
    # template alias
    "default": {
        "NAME": os.environ["PG_DATABASE"],
        "USER": os.environ.get("PG_USER"),
        "PASSWORD": os.environ.get("PG_PASSWORD"),
        "HOST": os.environ["PG_HOST"],
        "PORT": os.environ["PG_PORT"],
        "OPTIONS": {...},
        # This DB doesn't have any deps
        "TEST": {
            'DEPENDENCIES': []
        }
    },
    # reserved alias
    "central_db": {
        "NAME": os.environ["PG_DATABASE"],
        "USER": os.environ.get("PG_USER"),
        "PASSWORD": os.environ.get("PG_PASSWORD"),
        "HOST": os.environ["PG_HOST"],
        "PORT": os.environ["PG_PORT"],
        "OPTIONS": {...},
        # This DB doesn't have any deps
        "TEST": {
            'DEPENDENCIES': []
        }
    }
}
```

!!! note
If the `default` alias is marked as a *reserved alias*, then it is possible to skip
defining the `DEPENDENCIES` key but this is **highly unrecommended** as this can cause
unnecessary confusion when the configuration changes later on and also because *explicit is
better than implicit*.

### Custom test runner

The behavior of the default test runner provided by Django is as follows:

1. Creates test suites.
2. Identifies the DB aliases which should be picked for creating test databases.
3. Creates test databases on the selected set of aliases and applies DB migrations on each of them.
4. Runs all test suites.
5. Tears down the entire environment including all test databases which were created.

A more detailed version of the above can be found [here](https://docs.djangoproject.com/en/2.2/topics/testing/advanced/#using-different-testing-frameworks)

The second point highlights that every test suite which involves DB interaction in a multi-DB scenario,
could define the DB aliases that each test within the suite would interact with, at the `class` level, thereby
telling Django to create test databases for all those DB aliases.
For example:

```python
# consider the same `DATABASES` setting from the above example
from django.test import TestCase
class HospitalModelTest(TestCase):
    
    databases = {'default', 'central_db'}
    # This instructs Django to create test databases for the
    # `default` and `central_db` aliases. 

    def setUp(self):
        DefaultModel.objects.create(
            ...
        )
        CentralDbModel.objects.create(
            ...
        )

    def test_object_create(self):
        default_obj = SomeModel.objects.get(...)
        central_db_obj = CentralDbModel.objects.get(...)
        self.assertEqual(default_obj.some_attr, 'some_value')
        self.assertEqual(central_db_obj.some_attr, 'some_value')

```

!!! note
The `databases` attribute set at the class level could be a combination of
**template aliases** and **reserved aliases** or, if not set explicitly, would fall back to
the `default` alias.

When the above test case is run, it would fail due to the following reasons:

1. The template aliases present in the `databases` attribute is not tenant normalized. As a result,
   creation of test databases for these aliases would fail.
2. Since test DB creation fails, any ORM queries made within tests when run would subsequently fail.

To fix both the above problems, plug in the custom test runner as follows:

```python
# settings.py
...
TEST_RUNNER = 'tenant_router.orm_backends.django_orm.test_util.TenantAwareTestRunner'
...
```

### Other ORM libraries

Since the other ORM libraries that ship with this package do not have a well defined test strategy,
apps will have to implement their own testing strategy.

!!! important
If a custom test runner other than `TenantAwareTestRunner` is used, then it should
either take up the responsibility of setting the tenant context for the scope of the entire test
run or can delegate it potentially to the `setUpClass` or `setUp` methods of the individual
`TestCase` classes.

## The pre-fork problem

In order to scale and take advantage of the underlying hardware,
process managers (like Gunicorn, Celery etc.,) typically spawn multiple worker/child processes
using a [pre-fork server model](https://docs.gunicorn.org/en/stable/design.html#server-model).
Interestingly there are two variations of this model depending on when the fork actually happens.

* The master process forks itself first to spawn workers and then loads the Django app in
 each of the worker processes. This is the default behaviour in WSGI servers like 
 Gunicorn, uWSGI etc.,

* The master process loads the Django app first and then forks itself. This is the default
 behaviour in Celery. The same can be achieved in the WSGI servers mentioned above as well by
 enabling a specific setting. (For eg: In Gunicorn, this can be achieved by setting the
 `preload_app` to `True`)
 
For the pub/sub mechanism to work correctly, it is mandatory that a background event listener
(thread) be spawned in each of the worker processes to receive and process events.

Assuming that the code for launching the BG event listener (thread) is placed in the 
[ready](https://docs.djangoproject.com/en/3.1/ref/applications/#django.apps.AppConfig.ready) 
method of the `tenant_router` app, it would work fine for the first variant mentioned above
but would fail for the second variant since ***background threads launched in the parent
process don't survive a fork and hence won't be copied into the child processes***.

Also, apart from the *pre-fork* server model, it is possible to use other methods to launch 
child/worker processes, though they're not being widely used in practice. More info about
this can be found 
[here](https://docs.python.org/3/library/multiprocessing.html#contexts-and-start-methods).

Considering all the above mentioned cases, it is impossible for the library to determine the
right place to put code responsible for launching the backgound event listener (thread).

In order to solve this, the library exposes a callback which has to be invoked in
every child/worker process once it's spawned. **It is the responsibility of the developers to 
hook this callback in the right place so that it is invoked appropriately**.

For example, if [gunicorn](https://docs.gunicorn.org/en/latest/index.html) is being used, then 
in the [gunicorn.conf.py](https://docs.gunicorn.org/en/latest/configure.html#configuration-file) 
file, place the following code:

```python
# on_worker_init and on_worker_exit are the callbacks exposed by the library
# they should be imported and used as follows:
from tenant_router.bootstrap import on_worker_init, on_worker_exit   
...

def post_worker_init(worker):
    on_worker_init()


def worker_exit(server, worker):
    on_worker_exit()
```

> **NOTE**:
    The `on_worker_exit` callback is responsible for gracefully shutting down the
    background event listener (thread). Although it would be ideal if invoked
    from an appropriate hook, it is not entirely mandatory in case such a hook is unavailable. 

Similarly, if uWSGI is being used, then these callbacks could be invoked from the 
[post-fork](https://uwsgi-docs.readthedocs.io/en/latest/PythonDecorators.html#uwsgidecorators.postfork)
hook.

If, for some reason, the WSGI server doesn't expose such a hook, the low-level 
[register_at_fork](https://docs.python.org/3/library/os.html#os.register_at_fork) method can
be used, though this *might not work* on some platforms.

> **IMPORTANT**:
    If **Celery** is being used, then the app does not have to do anything as the library
    already hooks these callbacks to the 
    [worker_process_init](https://docs.celeryproject.org/en/stable/userguide/signals.html#worker-process-shutdown)
    and 
    [worker_process_shutdown](https://docs.celeryproject.org/en/stable/userguide/signals.html#worker-process-shutdown)
    signals.


