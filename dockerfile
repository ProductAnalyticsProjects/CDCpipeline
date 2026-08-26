FROM apache/spark:4.2.0

USER root

ADD https://repo1.maven.org/maven2/io/delta/delta-spark_2.13/4.0.0/delta-spark_2.13-4.0.0.jar /opt/spark/jars/
ADD https://repo1.maven.org/maven2/io/delta/delta-storage/3.3.0/delta-storage-3.3.0.jar /opt/spark/jars/
ADD https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.13/4.0.0/spark-sql-kafka-0-10_2.13-4.0.0.jar /opt/spark/jars/
ADD https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.9.0/kafka-clients-3.9.0.jar /opt/spark/jars/
ADD https://repo1.maven.org/maven2/org/apache/spark/spark-token-provider-kafka-0-10_2.13/4.0.0/spark-token-provider-kafka-0-10_2.13-4.0.0.jar /opt/spark/jars/
ADD https://repo1.maven.org/maven2/org/apache/commons/commons-pool2/2.12.1/commons-pool2-2.12.1.jar /opt/spark/jars/
ADD https://repo1.maven.org/maven2/software/amazon/awssdk/bundle/2.26.12/bundle-2.26.12.jar /opt/spark/jars/
ADD https://repo1.maven.org/maven2/org/postgresql/postgresql/42.7.3/postgresql-42.7.3.jar /opt/spark/jars/

RUN curl -o /opt/spark/jars/hadoop-aws-3.4.0.jar \
    https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.4.0/hadoop-aws-3.4.0.jar && \
    curl -o /opt/spark/jars/aws-java-sdk-bundle-1.12.262.jar \
    https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.262/aws-java-sdk-bundle-1.12.262.jar

RUN chmod 644 /opt/spark/jars/*.jar

ENV SPARK_CONF_spark_sql_extensions=io.delta.sql.DeltaSparkSessionExtension
ENV SPARK_CONF_spark_sql_catalog_spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog

COPY requirements.txt .
RUN pip install -r requirements.txt

USER spark
