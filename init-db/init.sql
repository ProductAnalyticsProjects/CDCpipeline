-- Idempotente: con POSTGRES_DB=ecommerce il database lo crea già
-- l'entrypoint ufficiale dell'immagine Postgres PRIMA di eseguire questo
-- script (che gira connesso a quel database) — un CREATE DATABASE diretto
-- fallirebbe con "already exists". In CI invece POSTGRES_DB=ci_test
-- (scripts/check_postgres_cdc_readiness.sh), quindi qui la creazione serve
-- davvero. \gexec esegue la query generata solo se non esiste già.
SELECT 'CREATE DATABASE ecommerce'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'ecommerce')\gexec
