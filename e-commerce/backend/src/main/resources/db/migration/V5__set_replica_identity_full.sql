-- Senza REPLICA IDENTITY FULL (il default Postgres logga solo la PK della
-- riga precedente), Debezium non può popolare `before` su UPDATE/DELETE: lo
-- schema di `before` richiede tutte le colonne, ma il WAL ne fornisce solo
-- una. Costo aggiunto trascurabile a questa scala: outbox_events e
-- order_items sono insert-only (nessun UPDATE/DELETE a cui FULL si applichi),
-- orders è l'unica tabella con update reali (transizioni di status).
ALTER TABLE orders REPLICA IDENTITY FULL;
ALTER TABLE users REPLICA IDENTITY FULL;
ALTER TABLE order_items REPLICA IDENTITY FULL;
ALTER TABLE outbox_events REPLICA IDENTITY FULL;
