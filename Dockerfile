FROM gcc:15 AS engine-builder

WORKDIR /app
COPY . .
RUN mkdir -p /app/public && \
    cp /app/index.html /app/public/index.html && \
    cp /app/admin.html /app/public/admin.html && \
    cp /app/app.js /app/public/app.js && \
    cp /app/admin.js /app/public/admin.js && \
    cp /app/styles.css /app/public/styles.css
RUN g++ -std=c++17 -Wall -Wextra \
    -I /app \
    /app/engine.cpp \
    /app/board.cpp \
    /app/mask.cpp \
    -o /app/engine

FROM python:3.13-slim

WORKDIR /app
COPY --from=engine-builder /app /app
RUN pip install --no-cache-dir -r requirements.txt
ENV PORT=8080
EXPOSE 8080
CMD ["python", "server.py"]
