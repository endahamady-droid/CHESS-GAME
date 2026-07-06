FROM gcc:15 AS engine-builder

WORKDIR /app
COPY . .
RUN g++ -std=c++17 -Wall -Wextra \
    -I /app \
    /app/engine.cpp \
    /app/board.cpp \
    /app/mask.cpp \
    -o /app/engine

FROM python:3.13-slim

WORKDIR /app
COPY --from=engine-builder /app /app
ENV PORT=8080
EXPOSE 8080
CMD ["python", "server.py"]