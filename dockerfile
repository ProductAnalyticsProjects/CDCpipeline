FROM apache/spark:4.0.0

# Passiamo a root per installare dipendenze e gestire i permessi
USER root

# Scarichiamo Delta Lake e il connettore Kafka per Spark 4 (Scala 2.13)
# Nota: Usiamo spark-submit per scaricare i jar nella cartella Ivy del container
RUN /opt/spark/bin/spark-submit \
    --packages io.delta:delta-spark_2.13:4.0.0,org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.0 \
    --help > /dev/null

# Configurazioni fisse per Delta Lake
ENV SPARK_CONF_spark_sql_extensions=io.delta.sql.DeltaSparkSessionExtension
ENV SPARK_CONF_spark_sql_catalog_spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog

# Se vuoi che i pacchetti siano sempre inclusi senza ridefinirli nello script:
ENV SPARK_CONF_spark_jars_packages=io.delta:delta-spark_2.13:4.0.0,org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.0

# Torniamo all'utente spark per sicurezza (opzionale, ma consigliato)
USER spark
