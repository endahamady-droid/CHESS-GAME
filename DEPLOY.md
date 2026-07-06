# Publish The Online Chess Site

GitHub is good for storing the code, but GitHub by itself does not run the Python server.
For your friend to open the game from another computer, deploy it on a hosting service.

## Recommended Simple Path

1. Publish the full project folder to GitHub.
2. Do not commit `online-server/chess_online.db`.
3. Use a host that supports Docker, for example Render, Fly.io, or Railway.
4. Set the Dockerfile path to:

```text
online-server/Dockerfile
```

5. Set the web port to:

```text
8080
```

6. Add environment variables for your admin account:

```text
ADMIN_USERNAME=your_admin_name
ADMIN_PASSWORD=choose_a_strong_password
```

After deployment, the host gives you a public URL like:

```text
https://your-game-name.onrender.com
```

Send that link to your friend.

## Important

The server creates its database file automatically. On free hosting, the database may reset when the host restarts unless you add persistent storage.

For a school/demo release, SQLite is okay. For a serious public release, move accounts and games to PostgreSQL.
