from tenant_router.bootstrap import on_worker_init, on_worker_exit


bind = '0.0.0.0:9000'
workers = 2


def post_worker_init(worker):
    on_worker_init()


def worker_exit(server, worker):
    on_worker_exit()
