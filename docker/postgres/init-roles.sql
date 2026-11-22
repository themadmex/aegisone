-- Local and CI database bootstrap. Runs once as the container superuser.
-- Development-only passwords: never reuse these outside a local machine or CI.
--
-- aegis_owner : owns the schema and runs migrations. Not a superuser and has no
--               BYPASSRLS, so FORCE ROW LEVEL SECURITY still applies to it.
-- aegis_app   : the runtime web role. Owns nothing, cannot bypass RLS and only
--               receives the table grants applied by migrations.

CREATE ROLE aegis_owner LOGIN PASSWORD 'aegis_owner_dev' NOSUPERUSER NOBYPASSRLS CREATEDB NOCREATEROLE;
CREATE ROLE aegis_app LOGIN PASSWORD 'aegis_app_dev' NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;

CREATE DATABASE aegisone OWNER aegis_owner;
