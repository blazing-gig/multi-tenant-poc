import json
from threading import Timer

import requests
import concurrent.futures

def test_get_books():
    headers = {"x-tenant-id": "tenant-1.test.com"}

    r = requests.get(
        "http://localhost:8000/api/hospital/",
        headers=headers
    )

    print(r.json())

def add_tenant():
    payload = {
        "tenant_id": "tenant-2.test.com",
        "deploy_info": {
            "POSTGRES_URL": "postgres://test_user:password@0.0.0.0:9700/tenant_2_db",
            "MONGO_URL": "mongodb://0.0.0.0:9800/tenant_2_db",
        }
    }

    r = requests.post(
        "http://localhost:9000/api/tenant/",
        json=payload
    )

    print(r.json())
    
def update_tenant():
    payload = {
        "deploy_info": {
            "POSTGRES_URL": "postgres://postgres:password@0.0.0.0:6000/postgres",
        }
    }

    r = requests.put(
        "http://localhost:9000/api/tenant/tenant-2.innovaccer.xyz/",
        json=payload
    )

    print(r.json())

def delete_tenant():
    r = requests.delete(
        "http://localhost:9000/api/tenant/tenant-1.innovaccer.xyz/",
    )

    print(r.json())

def health_check():

    r = requests.get(
        "http://localhost:9000/api/health-check/",
    )

    print(r.json())


def test_create_books():
    # headers = {"Host": "sample.com"}
    # data = {
    #     "name": "Angels and demons",
    #     "author": "Dan Brown"
    # }
    r = requests.get(
        "http://localhost:9000/api/mixed/",
        # headers = headers,
        # json = data
    )

    print(r.json())

def test_race_view():

    def hit_api(domain):
        r = requests.get(
            "http://localhost:9000/api/test/",
            headers={
                'Origin': "http://{0}:9000/".format(domain)
            }
        )

        return r.json()

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # Start the load operations and mark each future with its URL
        future_list = []

        for i in range(10):
            if i < 5:
                domain = 'service-1.innovaccer.com'
            else:
                domain = 'service-2.innovaccer.com'

            future_list.append(
                executor.submit(
                    hit_api,
                    domain
                )
            )

        # future_to_url = {executor.submit(load_url, url, 60): url for url in URLS}
        for index, future in enumerate(concurrent.futures.as_completed(future_list)):
            try:
                print(
                    "index is {0} result is {1} \n".format(index, future.result())
                )
                # print("job ", index, "succeeded\n")

            except Exception as exc:
                print('generated an exception: ', exc, str(index))


expected_result = [{'id': 1, 'name': 'apollo', 'address': 'Chennai'}]

def load_test():
    global expected_result

    def hit_api(tenant_id, expected_result):
        r = requests.get(
            "http://localhost:9000/api/hospital/",
            headers={
                'x-tenant-id': tenant_id
            }
        )
        print("expected_result is", expected_result)

        try:
            assert r.json() == expected_result
        except Exception as e:
            print("#### EXCEPTION is ", e)

        return expected_result

    def update_redis(*args, **kwargs):

        from redis import Redis
        r = Redis(host='0.0.0.0', db=5)
        updated_conf = {
            "HOST": "0.0.0.0",
            "PORT": "6001",
            "USER": "postgres",
            "PASSWORD": "password",
            "NAME": "postgres"
        }
        r.set('tenant_1_innovaccer_xyz_incare_orm_config_django_orm_default', json.dumps(
            updated_conf
        ))
        r.close()
        expected_result.clear()
        print("new expected_result is ", expected_result)

    def restore_redis():
        from redis import Redis
        r = Redis(host='0.0.0.0', db=5)
        updated_conf = {
            "HOST": "0.0.0.0",
            "PORT": "6000",
            "USER": "postgres",
            "PASSWORD": "password",
            "NAME": "postgres"
        }
        r.set('tenant_1_innovaccer_xyz_incare_orm_config_django_orm_default', json.dumps(
            updated_conf
        ))
        r.close()

    t = Timer(2.0, update_redis, [expected_result])
    t.start()


    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # Start the load operations and mark each future with its URL
        future_list = []

        for i in range(100):

            domain = 'tenant-1.innovaccer.xyz'
            future_list.append(
                executor.submit(
                    hit_api,
                    domain,
                    expected_result
                )
            )

        # future_to_url = {executor.submit(load_url, url, 60): url for url in URLS}
        for index, future in enumerate(concurrent.futures.as_completed(future_list)):
            try:
                print(
                    "index is {0} result is {1} \n".format(index, future.result())
                )
                # print("job ", index, "succeeded\n")

            except Exception as exc:
                print('generated an exception: ', exc, str(index))


    restore_redis()


# test_create_books()
test_get_books()
# add_tenant()
# delete_tenant()

# update_tenant()

# test_race_view()
# health_check()
# load_test()
