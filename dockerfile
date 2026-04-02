FROM apache/spark:4.0.0

# Passiamo a root per installare dipendenze e gestire i permessi
USER root

# Installiamo i JAR di Delta e Kafka direttamente nella cartella /opt/spark/jars
# Usiamo i link diretti dal repository Maven per essere sicuri al 100%
ADD https://repo1.maven.org/maven2/io/delta/delta-spark_2.13/4.0.0/delta-spark_2.13-4.0.0.jar /opt/spark/jars/
ADD https://repo1.maven.org/maven2/io/delta/delta-storage/3.3.0/delta-storage-3.3.0.jar /opt/spark/jars/
ADD https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.13/4.0.0/spark-sql-kafka-0-10_2.13-4.0.0.jar /opt/spark/jars/
ADD https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.9.0/kafka-clients-3.9.0.jar /opt/spark/jars/
ADD https://repo1.maven.org/maven2/org/apache/spark/spark-token-provider-kafka-0-10_2.13/4.0.0/spark-token-provider-kafka-0-10_2.13-4.0.0.jar /opt/spark/jars/
ADD https://repo1.maven.org/maven2/org/apache/commons/commons-pool2/2.12.1/commons-pool2-2.12.1.jar /opt/spark/jars/

# Sistemiamo i permessi
RUN chmod 644 /opt/spark/jars/*.jar

# Configurazioni fisse per Delta Lake
ENV SPARK_CONF_spark_sql_extensions=io.delta.sql.DeltaSparkSessionExtension
ENV SPARK_CONF_spark_sql_catalog_spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog

# Se vuoi che i pacchetti siano sempre inclusi senza ridefinirli nello script:
ENV SPARK_CONF_spark_jars_packages=io.delta:delta-spark_2.13:4.0.0,org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.0

# Torniamo all'utente spark per sicurezza (opzionale, ma consigliato)
USER spark
