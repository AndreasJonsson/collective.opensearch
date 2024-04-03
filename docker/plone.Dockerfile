FROM plone/plone-backend:6.0.0b3

WORKDIR /app

RUN /app/bin/pip install git+https://github.com/collective/collective.opensearch.git@mle-redis-rq#egg=collective.opensearch[redis]

ENV PROFILES="collective.opensearch:default collective.opensearch:docker-dev"
ENV TYPE="classic"
ENV SITE="Plone"
