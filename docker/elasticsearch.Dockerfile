FROM elasticsearch:7.17.7

RUN bin/elasticsearch-plugin install ingest-attachment -b
