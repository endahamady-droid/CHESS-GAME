const state = {
  token: localStorage.getItem("info7_token") || "",
  player: JSON.parse(localStorage.getItem("info7_player") || "null"),
  roomCode: localStorage.getItem("info7_room") || "",
  color: localStorage.getItem("info7_color") || "",
  selected: null,
  room: null,
  poller: null,
};

const pieces = {
  K: "WK",
  Q: "WQ",
  R: "WR",
  B: "WB",
  N: "WN",
  P: "WP",
  k: "BK",
  q: "BQ",
  r: "BR",
  b: "BB",
  n: "BN",
  p: "BP",
};

const files = "abcdefgh";

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
  if (state.token) {
    headers.Authorization = `Bearer ${state.token}`;
  }

  const response = await fetch(path, { ...options, headers });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "request_failed");
  }
  return data;
}

function saveSession() {
  if (state.token) localStorage.setItem("info7_token", state.token);
  else localStorage.removeItem("info7_token");

  if (state.player) localStorage.setItem("info7_player", JSON.stringify(state.player));
  else localStorage.removeItem("info7_player");

  if (state.roomCode) localStorage.setItem("info7_room", state.roomCode);
  else localStorage.removeItem("info7_room");

  if (state.color) localStorage.setItem("info7_color", state.color);
  else localStorage.removeItem("info7_color");
}

function showPanels() {
  const loggedIn = Boolean(state.token && state.player);
  $("authPanel").classList.toggle("hidden", loggedIn);
  $("roomPanel").classList.toggle("hidden", !loggedIn);
  $("gamePanel").classList.toggle("hidden", !loggedIn || !state.roomCode);
  if (loggedIn) $("playerName").textContent = state.player.username;
}

function fenToBoard(fen) {
  const board = [];
  const rows = fen.split("/");
  for (const row of rows) {
    const cells = [];
    for (const char of row) {
      if (/[1-8]/.test(char)) {
        for (let i = 0; i < Number(char); i++) cells.push("");
      } else {
        cells.push(char);
      }
    }
    board.push(cells);
  }
  return board;
}

function squareName(row, col) {
  return `${files[col]}${8 - row}`;
}

function renderBoard() {
  const boardElement = $("board");
  boardElement.innerHTML = "";
  const board = fenToBoard(state.room?.fen || "8/8/8/8/8/8/8/8");

  for (let row = 0; row < 8; row++) {
    for (let col = 0; col < 8; col++) {
      const square = document.createElement("button");
      const name = squareName(row, col);
      square.className = `square ${(row + col) % 2 === 0 ? "light" : "dark"}`;
      if (state.selected === name) square.classList.add("selected");

      const piece = board[row][col];
      if (piece) {
        const pieceElement = document.createElement("span");
        pieceElement.className = piece === piece.toUpperCase() ? "piece white-piece" : "piece black-piece";
        pieceElement.textContent = pieces[piece] || "";
        square.appendChild(pieceElement);
      }

      square.title = name;
      square.addEventListener("click", () => selectSquare(name));
      boardElement.appendChild(square);
    }
  }
}

function renderRoom() {
  if (!state.room) return;
  $("roomCode").textContent = state.room.code;
  $("turnText").textContent =
    state.room.status === "waiting"
      ? "Waiting for your friend"
      : `${state.room.turn === "white" ? "White" : "Black"} to move`;
  $("colorText").textContent = `Your color: ${state.color || "-"}`;
  $("statusText").textContent = `Status: ${state.room.status}`;

  const movesList = $("movesList");
  movesList.innerHTML = "";
  for (const move of state.room.moves || []) {
    const item = document.createElement("li");
    item.textContent = move.move_text;
    movesList.appendChild(item);
  }

  renderBoard();
}

async function loadRoom() {
  if (!state.roomCode) return;
  state.room = await api(`/api/rooms/${state.roomCode}`, { method: "GET" });
  renderRoom();
}

function startPolling() {
  if (state.poller) clearInterval(state.poller);
  if (!state.roomCode) return;
  loadRoom().catch((error) => message(error.message, true));
  state.poller = setInterval(() => {
    loadRoom().catch((error) => message(error.message, true));
  }, 1500);
}

function selectSquare(name) {
  if (!state.room || state.room.status !== "playing") return;
  if (!state.selected) {
    state.selected = name;
    renderBoard();
    return;
  }

  const move = `${state.selected}${name}`;
  state.selected = null;
  $("manualMove").value = move;
  renderBoard();
  sendMove(move);
}

async function sendMove(move) {
  try {
    await api(`/api/rooms/${state.roomCode}/moves`, {
      method: "POST",
      body: JSON.stringify({ move }),
    });
    $("manualMove").value = "";
    message(`Move sent: ${move}`);
    await loadRoom();
  } catch (error) {
    message(error.message, true);
  }
}

async function checkServer() {
  try {
    await api("/health", { method: "GET" });
    $("serverStatus").textContent = "Server online";
  } catch {
    $("serverStatus").textContent = "Server offline";
  }
}

$("registerBtn").addEventListener("click", async () => {
  try {
    await api("/api/register", {
      method: "POST",
      body: JSON.stringify({
        username: $("username").value,
        password: $("password").value,
      }),
    });
    message("Account created. Now login.");
  } catch (error) {
    message(error.message, true);
  }
});

$("loginBtn").addEventListener("click", async () => {
  try {
    const data = await api("/api/login", {
      method: "POST",
      body: JSON.stringify({
        username: $("username").value,
        password: $("password").value,
      }),
    });
    state.token = data.token;
    state.player = data.player;
    saveSession();
    if (data.player.is_admin) {
      localStorage.setItem("info7_admin_token", data.token);
      window.location.href = "/admin.html";
      return;
    }
    showPanels();
    message("Logged in.");
    startPolling();
  } catch (error) {
    message(error.message, true);
  }
});

$("logoutBtn").addEventListener("click", () => {
  state.token = "";
  state.player = null;
  state.roomCode = "";
  state.color = "";
  state.room = null;
  saveSession();
  showPanels();
  renderBoard();
  message("Logged out.");
});

$("createRoomBtn").addEventListener("click", async () => {
  try {
    const room = await api("/api/rooms", { method: "POST", body: "{}" });
    state.roomCode = room.code;
    state.color = room.color;
    saveSession();
    showPanels();
    startPolling();
    message(`Room created. Share code ${room.code} with your friend.`);
  } catch (error) {
    message(error.message, true);
  }
});

$("joinRoomBtn").addEventListener("click", async () => {
  try {
    const code = $("joinCode").value.trim().toUpperCase();
    const room = await api(`/api/rooms/${code}/join`, { method: "POST", body: "{}" });
    state.roomCode = room.code;
    state.color = room.color;
    saveSession();
    showPanels();
    startPolling();
    message(`Joined room ${room.code}.`);
  } catch (error) {
    message(error.message, true);
  }
});

$("copyCodeBtn").addEventListener("click", async () => {
  await navigator.clipboard.writeText(state.roomCode);
  message("Room code copied.");
});

$("sendMoveBtn").addEventListener("click", () => {
  const move = $("manualMove").value.trim().toLowerCase();
  if (!/^[a-h][1-8][a-h][1-8]$/.test(move)) {
    message("Use move format like e2e4.", true);
    return;
  }
  sendMove(move);
});

checkServer();
showPanels();
renderBoard();
startPolling();
