FROM node:22.23.4-alpine3.24@sha256:fe4f6d74e20370acb04ad889077d14d0f64a9c8ea6a42bc60cddf1e844699914 AS frontend-build
WORKDIR /build
COPY src/frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY src/frontend/ ./
RUN npm run build

FROM nginx:stable-alpine@sha256:47928bf67eb62a1863cb08d9ecb52d3e704304ba614eaee17884204677702951 AS frontend
COPY --from=frontend-build /build/dist /usr/share/nginx/html
COPY frontend.conf /etc/nginx/conf.d/default.conf

FROM python:3.12.16-slim@sha256:962f801b08c870ac2a51b72bf02dae38c9a4162319e5e882ec244e198188d54e AS backend
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY src/backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY src/backend/app ./app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
