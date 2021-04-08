create user test_user with createdb password 'password';

CREATE DATABASE tenant_1_db;
GRANT ALL PRIVILEGES ON DATABASE tenant_1_db TO test_user;

CREATE DATABASE tenant_2_db;
GRANT ALL PRIVILEGES ON DATABASE tenant_2_db TO test_user;