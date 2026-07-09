const storage = window.sessionStorage;

const state = {
  token: storage.getItem("info7_admin_token") || "",
};

function $(id) {
  return document.getElementById(id);
}

function message(text, isError = false) {
  $("message").textContent = text;
  $("message").style.color = isError ? "#b91c1c" : "#166534";
}

async function api(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;

  const response = await fetch(path, { ...options, headers });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "request_failed");
  return data;
}

function showAdmin(show) {
  $("loginPanel").classList.toggle("hidden", show);
  $("adminPanel").classList.toggle("hidden", !show);
  $("roomsPanel").classList.toggle("hidden", !show);
  $("databasePanel").classList.toggle("hidden", !show);
}

async function login() {
  try {
    const data = await api("/api/login", {
      method: "POST",
      body: JSON.stringify({
        username: $("username").value,
        password: $("password").value,
      }),
    });
    if (!data.player.is_admin) {
      message("This account is not admin.", true);
      return;
    }
    state.token = data.token;
    storage.setItem("info7_admin_token", state.token);
    showAdmin(true);
    await loadDashboard();
  } catch (error) {
    message(error.message, true);
  }
}

async function adminAction(playerId, action) {
  try {
    await api(`/api/admin/players/${playerId}/${action}`, {
      method: "POST",
      body: "{}",
    });
    message("Action saved.");
    await loadDashboard();
  } catch (error) {
    message(error.message, true);
  }
}

function renderPlayers(players) {
  const table = $("playersTable");
  table.innerHTML = "";

  for (const player of players) {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${player.id}</td>
      <td>${player.username}</td>
      <td>${player.is_admin ? "Admin" : "Player"}</td>
      <td>${player.is_disabled ? "Disabled" : "Active"}</td>
      <td>${player.wins}W / ${player.losses}L / ${player.draws}D</td>
      <td class="table-actions"></td>
    `;

    const actions = row.querySelector(".table-actions");
    const disableButton = document.createElement("button");
    disableButton.textContent = player.is_disabled ? "Enable" : "Disable";
    disableButton.className = "secondary small";
    disableButton.addEventListener("click", () => adminAction(player.id, player.is_disabled ? "enable" : "disable"));
    actions.appendChild(disableButton);

    const adminButton = document.createElement("button");
    adminButton.textContent = player.is_admin ? "Remove admin" : "Make admin";
    adminButton.className = "secondary small";
    adminButton.addEventListener("click", () => adminAction(player.id, player.is_admin ? "remove-admin" : "make-admin"));
    actions.appendChild(adminButton);

    table.appendChild(row);
  }
}

function renderRooms(rooms) {
  const table = $("roomsTable");
  table.innerHTML = "";

  for (const room of rooms) {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${room.code}</td>
      <td>${room.white_username || "-"}</td>
      <td>${room.black_username || "-"}</td>
      <td>${room.status}</td>
      <td>${room.turn}</td>
    `;
    table.appendChild(row);
  }
}

function renderDatabase(database) {
  $("databasePath").textContent = database.path;
  $("databaseSize").textContent = `${database.size_bytes} bytes`;
  $("databasePlayers").textContent = database.players;
  $("databaseRooms").textContent = database.rooms;
  $("databaseMoves").textContent = database.moves;
}

async function loadDashboard() {
  try {
    const players = await api("/api/admin/players", { method: "GET" });
    const rooms = await api("/api/admin/rooms", { method: "GET" });
    const database = await api("/api/admin/database", { method: "GET" });
    renderPlayers(players.players);
    renderRooms(rooms.rooms);
    renderDatabase(database);
    showAdmin(true);
  } catch (error) {
    showAdmin(false);
    message(error.message, true);
  }
}

$("loginBtn").addEventListener("click", login);
$("refreshBtn").addEventListener("click", loadDashboard);

if (state.token) {
  loadDashboard();
} else {
  showAdmin(false);
}
