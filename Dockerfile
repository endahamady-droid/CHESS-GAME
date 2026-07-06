FROM gcc:15 AS engine-builder

WORKDIR /app
COPY . .
RUN g++ -std=c++17 -Wall -Wextra \
    -I /app \
    /app/online-server/engine.cpp \
    /app/board.cpp \
    /app/game.cpp \
    /app/mask.cpp \
    -o /app/online-server/engine

FROM python:3.13-slim

WORKDIR /app
COPY --from=engine-builder /app/online-server /app/online-server

WORKDIR /app/online-server
ENV PORT=8080
EXPOSE 8080
CMD ["python", "server.py"]
