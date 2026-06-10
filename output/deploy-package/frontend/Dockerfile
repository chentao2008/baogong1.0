FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html /usr/share/nginx/html/index.html
COPY styles.css /usr/share/nginx/html/styles.css
COPY app.js /usr/share/nginx/html/app.js
COPY admin-query-helpers.js /usr/share/nginx/html/admin-query-helpers.js
COPY report-swipe-helpers.js /usr/share/nginx/html/report-swipe-helpers.js

EXPOSE 80
