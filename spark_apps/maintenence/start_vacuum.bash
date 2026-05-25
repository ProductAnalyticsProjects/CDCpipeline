docker exec spark-master \
  /opt/spark/bin/spark-submit \
  --master spark://spark-master:7077 \
  /opt/spark/apps/maintenance/vacuum.py
