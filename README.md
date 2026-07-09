# INFO7 Online Chess Server

This server keeps your existing C++ chess logic separate and unchanged.

It uses:

- `server.py` for accounts, rooms, moves, and SQLite database storage.
- PostgreSQL automatically when `DATABASE_URL` is configured on Render.
- `engine.cpp` as a small C++ adapter around your existing `board.cpp`, `game.cpp`, and `mask.cpp`.
- `chess_online.db` as the local fallback database file created automatically.

## Build the C++ rule engine

From this folder:

```powershell
.\build_engine.ps1
```

The script compiles `engine.exe` using files from:

```text
C:\INFO7VERSION CLAUDE
```

Your original C++ files are not edited.

## Start the server

```powershell
python .\server.py
```

The server starts on:

```text
http://localhost:8080
```

Open this address in a browser to use the online chess site.

If Windows says `python` is not recognized, install Python from python.org or run it with the full path to your Python executable.

## Admin account

The server creates an admin account automatically:

```text
username: babba
password: 130577
```

Open the admin page:

```text
http://localhost:8080/admin.html
```

You can also login with this account on the normal site. Admin users are redirected to the admin page automatically.

The admin dashboard shows the database path, database size, players count, rooms count, and moves count.

## Persistent production database

For Render, create a PostgreSQL database and set `DATABASE_URL` on the Web Service. The server runs migrations automatically and stores users, ELO, quiz progress, sessions, chat, rooms, moves, and game history there.

See `SECURITY_DEPLOY.md` for Render variables, OAuth variables, and Cloudflare/security setup.

For a real online deployment, change the admin credentials with environment variables:

```text
ADMIN_USERNAME=your_admin_name
ADMIN_PASSWORD=a-strong-password
```

## Website flow

1. Open `http://localhost:8080`.
2. Create an account or login.
3. Click `Create room`.
4. Send the room code to your friend.
5. Your friend opens the same website and joins with the code.
6. Click a piece and then the target square, or type a move like `e2e4`.

For friends outside your home network, publish the project to GitHub and deploy the server on a host that can run Python plus the included C++ `engine`.

See `DEPLOY.md` for the GitHub/deployment steps.

## API quick test

Register two players:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8080/api/register -ContentType application/json -Body '{"username":"alice","password":"1234"}'
Invoke-RestMethod -Method Post -Uri http://localhost:8080/api/register -ContentType application/json -Body '{"username":"bob","password":"1234"}'
```

Login:

```powershell
$alice = Invoke-RestMethod -Method Post -Uri http://localhost:8080/api/login -ContentType application/json -Body '{"username":"alice","password":"1234"}'
$bob = Invoke-RestMethod -Method Post -Uri http://localhost:8080/api/login -ContentType application/json -Body '{"username":"bob","password":"1234"}'
```

Create and join a room:

```powershell
$room = Invoke-RestMethod -Method Post -Uri http://localhost:8080/api/rooms -Headers @{Authorization="Bearer $($alice.token)"}
Invoke-RestMethod -Method Post -Uri "http://localhost:8080/api/rooms/$($room.code)/join" -Headers @{Authorization="Bearer $($bob.token)"}
```

Play moves:

```powershell
Invoke-RestMethod -Method Post -Uri "http://localhost:8080/api/rooms/$($room.code)/moves" -Headers @{Authorization="Bearer $($alice.token)"} -ContentType application/json -Body '{"move":"e2e4"}'
Invoke-RestMethod -Method Post -Uri "http://localhost:8080/api/rooms/$($room.code)/moves" -Headers @{Authorization="Bearer $($bob.token)"} -ContentType application/json -Body '{"move":"e7e5"}'
```

Read room state:

```powershell
Invoke-RestMethod -Method Get -Uri "http://localhost:8080/api/rooms/$($room.code)"
```
