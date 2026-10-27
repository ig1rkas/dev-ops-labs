FROM idioma-labs/frontend:lab0
COPY nginx/nginx.conf /etc/nginx/nginx.conf
RUN rm -f /etc/nginx/conf.d/default.conf
COPY site/ /srv/
