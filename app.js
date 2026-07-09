const storage = window.sessionStorage;

const state = {
  token: storage.getItem("info7_token") || "",
  player: JSON.parse(storage.getItem("info7_player") || "null"),
  roomCode: storage.getItem("info7_room") || "",
  color: storage.getItem("info7_color") || "",
  selected: null,
  room: null,
  chat: [],
  poller: null,
};

const pieces = {
  K: String.fromCodePoint(0x2654),
  Q: String.fromCodePoint(0x2655),
  R: String.fromCodePoint(0x2656),
  B: String.fromCodePoint(0x2657),
  N: String.fromCodePoint(0x2658),
  P: String.fromCodePoint(0x2659),
  k: String.fromCodePoint(0x265A),
  q: String.fromCodePoint(0x265B),
  r: String.fromCodePoint(0x265C),
  b: String.fromCodePoint(0x265D),
  n: String.fromCodePoint(0x265E),
  p: String.fromCodePoint(0x265F),
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
  if (state.token) storage.setItem("info7_token", state.token);
  else storage.removeItem("info7_token");

  if (state.player) storage.setItem("info7_player", JSON.stringify(state.player));
  else storage.removeItem("info7_player");

  if (state.roomCode) storage.setItem("info7_room", state.roomCode);
  else storage.removeItem("info7_room");

  if (state.color) storage.setItem("info7_color", state.color);
  else storage.removeItem("info7_color");
}

function showPanels() {
  const loggedIn = Boolean(state.token && state.player);
  const inGame = Boolean(loggedIn && state.roomCode);
  $("heroPanel").classList.toggle("hidden", inGame);
  $("authPanel").classList.toggle("hidden", loggedIn);
  $("roomPanel").classList.toggle("hidden", !loggedIn || inGame);
  $("gamePanel").classList.toggle("hidden", !inGame);
  document.body.classList.toggle("game-view", inGame);
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

function pieceColor(piece) {
  if (!piece) return "";
  return piece === piece.toUpperCase() ? "white" : "black";
}

function currentBoard() {
  return fenToBoard(state.room?.fen || "8/8/8/8/8/8/8/8");
}

function boardPieceAt(square) {
  const file = files.indexOf(square[0]);
  const rank = Number(square[1]);
  if (file < 0 || rank < 1 || rank > 8) return "";
  return currentBoard()[8 - rank]?.[file] || "";
}

function canMoveNow() {
  return Boolean(state.room && state.room.status === "playing" && state.room.turn === state.color);
}

function renderBoard() {
  const boardElement = $("board");
  boardElement.innerHTML = "";
  const board = currentBoard();

  for (let row = 0; row < 8; row++) {
    for (let col = 0; col < 8; col++) {
      const square = document.createElement("button");
      const name = squareName(row, col);
      square.className = `square ${(row + col) % 2 === 0 ? "light" : "dark"}`;
      if (state.selected === name) square.classList.add("selected");
      if (!canMoveNow()) square.classList.add("locked");
      if (row === 7) square.dataset.file = files[col];
      if (col === 0) square.dataset.rank = String(8 - row);

      const piece = board[row][col];
      if (piece) {
        const pieceElement = document.createElement("span");
        const colorClass = pieceColor(piece) === "white" ? "white-piece" : "black-piece";
        const typeClass = `piece-${piece.toLowerCase()}`;
        pieceElement.className = `piece ${colorClass} ${typeClass}`;
        pieceElement.textContent = pieces[piece] || "";
        square.appendChild(pieceElement);
        if (pieceColor(piece) === state.color) square.classList.add("own-piece");
      }

      square.title = name;
      square.addEventListener("click", (event) => selectSquare(name, event));
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
  $("statusText").textContent =
    state.room.status === "playing"
      ? "Status: opponent connected, game is live"
      : "Status: waiting for opponent";
  $("chatStatus").textContent =
    state.room.status === "playing" ? "Live chat" : "Chat will be ready when your friend joins";

  const movesList = $("movesList");
  movesList.innerHTML = "";
  for (const move of state.room.moves || []) {
    const item = document.createElement("li");
    item.textContent = move.move_text;
    movesList.appendChild(item);
  }

  renderBoard();
  renderChat();
}

async function loadRoom() {
  if (!state.roomCode) return;
  state.room = await api(`/api/rooms/${state.roomCode}`, { method: "GET" });
  renderRoom();
}

async function loadChat() {
  if (!state.roomCode) return;
  const data = await api(`/api/rooms/${state.roomCode}/chat`, { method: "GET" });
  state.chat = data.messages || [];
  renderChat();
}

function startPolling() {
  if (state.poller) clearInterval(state.poller);
  if (!state.roomCode) return;
  loadRoom().catch((error) => message(error.message, true));
  loadChat().catch(() => {});
  state.poller = setInterval(() => {
    loadRoom().catch((error) => message(error.message, true));
    loadChat().catch(() => {});
  }, 1500);
}

function selectSquare(name, event) {
  event?.currentTarget?.blur();
  if (!state.room || state.room.status !== "playing") {
    state.selected = null;
    renderBoard();
    message("Wait until your friend joins the room.", true);
    return;
  }

  if (state.room.turn !== state.color) {
    state.selected = null;
    renderBoard();
    message("Wait for your turn.", true);
    return;
  }

  const clickedPiece = boardPieceAt(name);
  if (!state.selected) {
    if (!clickedPiece) return;
    if (pieceColor(clickedPiece) !== state.color) {
      message("Choose one of your own pieces.", true);
      return;
    }
    state.selected = name;
    renderBoard();
    return;
  }

  if (state.selected === name) {
    state.selected = null;
    renderBoard();
    return;
  }

  if (clickedPiece && pieceColor(clickedPiece) === state.color) {
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
    state.selected = null;
    renderBoard();
    message(error.message, true);
  }
}

function renderChat() {
  const chatMessages = $("chatMessages");
  if (!chatMessages) return;

  chatMessages.innerHTML = "";
  for (const item of state.chat || []) {
    const bubble = document.createElement("div");
    const isMine = state.player && item.player_id === state.player.id;
    bubble.className = `chat-message ${isMine ? "mine" : "theirs"}`;

    const author = document.createElement("span");
    author.className = "chat-author";
    author.textContent = isMine ? "You" : item.username;

    const text = document.createElement("p");
    text.textContent = item.message;

    bubble.appendChild(author);
    bubble.appendChild(text);
    chatMessages.appendChild(bubble);
  }

  chatMessages.scrollTop = chatMessages.scrollHeight;
}

async function sendChat() {
  const input = $("chatInput");
  const text = input.value.trim();
  if (!text) return;

  try {
    await api(`/api/rooms/${state.roomCode}/chat`, {
      method: "POST",
      body: JSON.stringify({ message: text }),
    });
    input.value = "";
    await loadChat();
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
      storage.setItem("info7_admin_token", data.token);
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
  state.chat = [];
  state.selected = null;
  if (state.poller) clearInterval(state.poller);
  saveSession();
  showPanels();
  renderBoard();
  message("Logged out.");
});

$("leaveRoomBtn").addEventListener("click", () => {
  state.roomCode = "";
  state.color = "";
  state.room = null;
  state.chat = [];
  state.selected = null;
  if (state.poller) clearInterval(state.poller);
  saveSession();
  showPanels();
  renderBoard();
  renderChat();
  message("Back to lobby.");
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

$("sendChatBtn").addEventListener("click", sendChat);
$("chatInput").addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    sendChat();
  }
});

checkServer();
showPanels();
renderBoard();
startPolling();
