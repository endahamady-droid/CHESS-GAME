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
  renderedBoard: [],
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

const quizQuestions = [
  {
    question: "Which piece can move in an L shape?",
    options: ["Knight", "Bishop", "Rook", "Queen"],
    answer: 0,
  },
  {
    question: "What is the name of the move where the king and rook move together?",
    options: ["Fork", "Castling", "Promotion", "En passant"],
    answer: 1,
  },
  {
    question: "Which opening begins with 1. e4 e5 2. Nf3 Nc6 3. Bb5?",
    options: ["Sicilian Defense", "French Defense", "Ruy Lopez", "London System"],
    answer: 2,
  },
  {
    question: "What happens when a pawn reaches the last rank?",
    options: ["It is removed", "It promotes", "It becomes a king", "The game ends"],
    answer: 1,
  },
  {
    question: "What is checkmate?",
    options: ["A captured queen", "A draw offer", "A king in unavoidable check", "A pawn promotion"],
    answer: 2,
  },
];

const chessFacts = [
  "The longest possible chess game is often estimated at thousands of moves under older rule interpretations.",
  "The queen was once a much weaker piece before modern chess rules made it the most powerful attacker.",
  "The word checkmate comes from a phrase meaning the king is helpless.",
  "A knight always changes square color every time it moves.",
  "The first moves of a game are called the opening, and many have names that are centuries old.",
];

const quizState = {
  index: 0,
  score: 0,
};

const levelQuizState = {
  level: 1,
  index: 0,
  score: 0,
  questions: [],
};

function $(id) {
  return document.getElementById(id);
}

function message(text, isError = false) {
  $("message").textContent = text;
  $("message").style.color = isError ? "#b91c1c" : "#166534";
  $("message").classList.toggle("error", isError);
  $("message").classList.toggle("ok", Boolean(text && !isError));
}

async function api(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };
  if (state.token) {
    headers.Authorization = `Bearer ${state.token}`;
  }

  const response = await fetch(path, { ...options, headers, credentials: "include" });
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
  $("profilePanel").classList.toggle("hidden", !loggedIn || inGame);
  $("gamePanel").classList.toggle("hidden", !inGame);
  $("lobbyExtras").classList.toggle("hidden", inGame);
  document.body.classList.toggle("game-view", inGame);
  document.body.dataset.playerColor = state.color || "";
  if (loggedIn) $("playerName").textContent = state.player.username;
  if (loggedIn) updateProfileUI();
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

function lastMoveSquares() {
  const moves = state.room?.moves || [];
  const lastMove = moves[moves.length - 1]?.move_text || "";
  if (!/^[a-h][1-8][a-h][1-8]$/.test(lastMove)) return [];
  return [lastMove.slice(0, 2), lastMove.slice(2, 4)];
}

function ensureBoardSquares(boardElement) {
  if (boardElement.dataset.ready === "true" && boardElement.children.length === 64) return;

  boardElement.innerHTML = "";
  for (let row = 0; row < 8; row++) {
    for (let col = 0; col < 8; col++) {
      const square = document.createElement("button");
      const name = squareName(row, col);
      square.dataset.square = name;
      square.dataset.row = String(row);
      square.dataset.col = String(col);
      square.title = name;
      if (row === 7) square.dataset.file = files[col];
      if (col === 0) square.dataset.rank = String(8 - row);
      if (row === 7) {
        const fileLabel = document.createElement("span");
        fileLabel.className = "coord-file";
        fileLabel.textContent = files[col];
        square.appendChild(fileLabel);
      }
      square.addEventListener("click", (event) => selectSquare(name, event));
      boardElement.appendChild(square);
    }
  }
  boardElement.dataset.ready = "true";
  state.renderedBoard = Array(64).fill(null);
}

function updateSquarePiece(square, piece, previousPiece) {
  let pieceElement = square.querySelector(".piece");
  if (!piece) {
    if (pieceElement) {
      pieceElement.dataset.removing = "true";
      pieceElement.classList.add("piece-exit");
      window.setTimeout(() => {
        if (pieceElement.dataset.removing === "true") pieceElement.remove();
      }, 180);
    }
    return;
  }

  const colorClass = pieceColor(piece) === "white" ? "white-piece" : "black-piece";
  const typeClass = `piece-${piece.toLowerCase()}`;
  if (!pieceElement) {
    pieceElement = document.createElement("span");
    square.prepend(pieceElement);
  }
  delete pieceElement.dataset.removing;
  pieceElement.className = `piece ${colorClass} ${typeClass}`;
  pieceElement.textContent = pieces[piece] || "";
  pieceElement.classList.toggle("piece-moved", Boolean(previousPiece !== undefined && previousPiece !== piece));
}

function renderBoard() {
  const boardElement = $("board");
  ensureBoardSquares(boardElement);
  const board = currentBoard();
  const lastSquares = lastMoveSquares();

  for (let row = 0; row < 8; row++) {
    for (let col = 0; col < 8; col++) {
      const index = row * 8 + col;
      const square = boardElement.children[index];
      const name = squareName(row, col);
      const piece = board[row][col];
      const previousPiece = state.renderedBoard[index];
      square.className = `square ${(row + col) % 2 === 0 ? "light" : "dark"}`;
      if (state.selected === name) square.classList.add("selected");
      if (lastSquares.includes(name)) square.classList.add("last-move");
      if (!canMoveNow()) square.classList.add("locked");
      if (pieceColor(piece) === state.color) square.classList.add("own-piece");
      if (piece !== previousPiece) updateSquarePiece(square, piece, previousPiece);
      state.renderedBoard[index] = piece;
    }
  }
}

function renderRoom() {
  if (!state.room) return;
  $("gamePanel").classList.toggle("room-waiting", state.room.status === "waiting");
  $("gamePanel").classList.toggle("room-playing", state.room.status === "playing");
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
  const moves = state.room.moves || [];
  for (const [index, move] of moves.entries()) {
    const item = document.createElement("li");
    if (index === moves.length - 1) item.classList.add("latest-move");

    const number = document.createElement("span");
    number.className = "move-number";
    number.textContent = String(index + 1);

    const text = document.createElement("span");
    text.className = "move-text";
    text.textContent = move.move_text;

    item.appendChild(number);
    item.appendChild(text);
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

    const avatar = document.createElement("span");
    avatar.className = "chat-avatar";
    avatar.textContent = (isMine ? "Y" : item.username || "?").slice(0, 1).toUpperCase();

    const body = document.createElement("div");
    body.className = "chat-bubble";

    const author = document.createElement("span");
    author.className = "chat-author";
    const authorName = document.createElement("span");
    authorName.textContent = isMine ? "You" : item.username;
    const time = document.createElement("span");
    time.className = "chat-time";
    time.textContent = formatTime(item.created_at);
    author.appendChild(authorName);
    author.appendChild(time);

    const text = document.createElement("p");
    text.textContent = item.message;

    body.appendChild(author);
    body.appendChild(text);
    bubble.appendChild(avatar);
    bubble.appendChild(body);
    chatMessages.appendChild(bubble);
  }

  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function formatTime(timestamp) {
  if (!timestamp) return "";
  return new Date(timestamp * 1000).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
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

async function loadProfile() {
  if (!state.token) return;
  try {
    const data = await api("/api/profile", { method: "GET" });
    state.player = data.player;
    saveSession();
    updateProfileUI();
    await loadHistory();
  } catch {
  }
}

async function loadHistory() {
  const list = $("historyList");
  if (!list || !state.token) return;
  try {
    const data = await api("/api/me/history", { method: "GET" });
    list.innerHTML = "";
    for (const game of data.history || []) {
      const item = document.createElement("li");
      const delta = Number(game.elo_delta);
      item.className = delta >= 0 ? "elo-up" : "elo-down";
      item.textContent = `${game.result} vs ${game.opponent_username || "unknown"} | ${delta >= 0 ? "+" : ""}${delta} ELO`;
      list.appendChild(item);
    }
    if (!list.children.length) {
      const item = document.createElement("li");
      item.textContent = "No finished games yet.";
      list.appendChild(item);
    }
  } catch {
  }
}

function updateProfileUI() {
  if (!state.player) return;
  $("profileLine").textContent = `ELO: ${state.player.elo || 1200} | Games: ${state.player.games_played || 0}`;
  $("profileElo").textContent = `ELO ${state.player.elo || 1200}`;
  $("profileRecord").textContent = `${state.player.wins || 0}W / ${state.player.losses || 0}L / ${state.player.draws || 0}D`;
  $("profileQuiz").textContent = `Quiz level ${state.player.quiz_level_reached || 1}`;
  $("profileGames").textContent = `${state.player.games_played || 0} games`;
}

async function completeLogin(data) {
  state.token = data.token;
  state.player = data.player;
  saveSession();
  if (data.player.is_admin) {
    storage.setItem("info7_admin_token", data.token);
    window.location.href = "/admin.html";
    return;
  }
  showPanels();
  await loadProfile();
  message("Logged in.");
  maybeOpenLevelQuiz();
  startPolling();
}

$("registerBtn").addEventListener("click", async () => {
  try {
    await api("/api/register", {
      method: "POST",
      body: JSON.stringify({
        username: $("username").value,
        email: $("email").value,
        password: $("password").value,
        elo: Number($("eloInput").value),
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
    await completeLogin(data);
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

$("playOnlineBtn").addEventListener("click", async () => {
  const button = $("playOnlineBtn");
  const oldText = button.textContent;
  button.disabled = true;
  button.textContent = "Finding match...";
  try {
    const room = await api("/api/matchmaking", { method: "POST", body: "{}" });
    state.roomCode = room.code;
    state.color = room.color;
    saveSession();
    showPanels();
    startPolling();
    message(room.matched ? `Match found. Room ${room.code}.` : "Waiting for an online opponent...");
  } catch (error) {
    message(error.message, true);
  } finally {
    button.disabled = false;
    button.textContent = oldText;
  }
});

$("sendChatBtn").addEventListener("click", sendChat);
$("chatInput").addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    sendChat();
  }
});

for (const input of [$("username"), $("password")]) {
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      $("loginBtn").click();
    }
  });
}

$("eloInput").addEventListener("input", () => {
  $("eloValue").textContent = $("eloInput").value;
});

$("joinCode").addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    $("joinRoomBtn").click();
  }
});

function enhanceButtons() {
  for (const element of document.querySelectorAll("button:not(.square), .button-link")) {
    element.addEventListener("click", (event) => {
      const ripple = document.createElement("span");
      const rect = element.getBoundingClientRect();
      ripple.className = "ripple";
      ripple.style.left = `${event.clientX - rect.left}px`;
      ripple.style.top = `${event.clientY - rect.top}px`;
      element.appendChild(ripple);
      window.setTimeout(() => ripple.remove(), 650);
    });
  }
}

function renderQuiz() {
  const question = quizQuestions[quizState.index];
  $("quizProgress").textContent = `${quizState.index + 1} / ${quizQuestions.length}`;
  $("quizQuestion").textContent = question.question;
  $("quizFeedback").textContent = "";
  $("quizReplayBtn").classList.add("hidden");

  const options = $("quizOptions");
  options.innerHTML = "";
  for (const [index, option] of question.options.entries()) {
    const button = document.createElement("button");
    button.className = "quiz-option secondary";
    button.textContent = option;
    button.addEventListener("click", () => answerQuiz(index));
    options.appendChild(button);
  }
}

function answerQuiz(answerIndex) {
  const question = quizQuestions[quizState.index];
  const isCorrect = answerIndex === question.answer;
  if (isCorrect) quizState.score++;

  for (const [index, button] of $("quizOptions").querySelectorAll("button").entries()) {
    button.disabled = true;
    button.classList.toggle("correct", index === question.answer);
    button.classList.toggle("wrong", index === answerIndex && !isCorrect);
  }

  $("quizFeedback").textContent = isCorrect ? "Correct. Nice eye." : "Not this time. Keep warming up.";
  window.setTimeout(() => {
    quizState.index++;
    if (quizState.index >= quizQuestions.length) {
      showQuizResult();
      return;
    }
    renderQuiz();
  }, 850);
}

function showQuizResult() {
  $("quizProgress").textContent = "Complete";
  $("quizQuestion").textContent = `Score: ${quizState.score} / ${quizQuestions.length}`;
  $("quizOptions").innerHTML = "";
  $("quizFeedback").textContent =
    quizState.score >= 4 ? "Sharp prep. You are ready for the board." : "Good warmup. Replay and sharpen the tactics.";
  $("quizReplayBtn").classList.remove("hidden");
}

$("quizReplayBtn").addEventListener("click", () => {
  quizState.index = 0;
  quizState.score = 0;
  renderQuiz();
});

function buildLevelQuestions(level) {
  const pool = [
    ...quizQuestions,
    { question: "What does O-O mean in algebraic notation?", options: ["Long castle", "Short castle", "Checkmate", "Capture"], answer: 1 },
    { question: "What is a fork?", options: ["A draw rule", "Attacking two pieces at once", "A pawn move", "A king escape"], answer: 1 },
    { question: "Which endgame is usually a forced mate?", options: ["King vs king", "King and queen vs king", "King and bishop vs king", "King and knight vs king"], answer: 1 },
    { question: "What is en passant?", options: ["A special pawn capture", "A rook move", "A queen trade", "A checkmate pattern"], answer: 0 },
    { question: "What symbol often means check in notation?", options: ["+", "#", "x", "="], answer: 0 },
    { question: "What is opposition in king endgames?", options: ["A tactic with queens", "Kings facing with one square between", "A castle move", "A time control"], answer: 1 },
    { question: "What does promotion usually choose?", options: ["King", "Queen", "Pawn", "No piece"], answer: 1 },
    { question: "What is a pin?", options: ["A piece cannot move safely because it exposes a stronger piece", "A draw", "A pawn race", "A castle"], answer: 0 },
  ];
  const count = Math.min(40, level * 5);
  const questions = [];
  for (let i = 0; i < count; i++) questions.push(pool[(i + level - 1) % pool.length]);
  return questions;
}

function maybeOpenLevelQuiz() {
  if (!state.player) return;
  const level = Number(state.player.quiz_level_reached || 1);
  if (level > 8) return;
  levelQuizState.level = level;
  levelQuizState.index = 0;
  levelQuizState.score = 0;
  levelQuizState.questions = buildLevelQuestions(level);
  $("quizModal").classList.remove("hidden");
  renderLevelQuiz();
}

function renderLevelQuiz() {
  const total = levelQuizState.questions.length;
  const question = levelQuizState.questions[levelQuizState.index];
  $("levelQuizTitle").textContent = `Level ${levelQuizState.level} Quiz`;
  $("levelProgressText").textContent = `Question ${levelQuizState.index + 1} / ${total}`;
  $("levelProgressBar").style.width = `${Math.round((levelQuizState.index / total) * 100)}%`;
  $("levelQuizQuestion").textContent = question.question;
  $("levelQuizFeedback").textContent = "";
  const options = $("levelQuizOptions");
  options.innerHTML = "";
  for (const [index, option] of question.options.entries()) {
    const button = document.createElement("button");
    button.className = "quiz-option secondary";
    button.textContent = option;
    button.addEventListener("click", () => answerLevelQuiz(index));
    options.appendChild(button);
  }
}

async function answerLevelQuiz(answerIndex) {
  const question = levelQuizState.questions[levelQuizState.index];
  const isCorrect = answerIndex === question.answer;
  if (isCorrect) levelQuizState.score++;
  for (const [index, button] of $("levelQuizOptions").querySelectorAll("button").entries()) {
    button.disabled = true;
    button.classList.toggle("correct", index === question.answer);
    button.classList.toggle("wrong", index === answerIndex && !isCorrect);
  }
  window.setTimeout(async () => {
    levelQuizState.index++;
    if (levelQuizState.index < levelQuizState.questions.length) {
      renderLevelQuiz();
      return;
    }
    const score = Math.round((levelQuizState.score / levelQuizState.questions.length) * 100);
    const passed = score >= 70;
    $("levelProgressBar").style.width = "100%";
    $("levelQuizQuestion").textContent = `${score}% score`;
    $("levelQuizOptions").innerHTML = "";
    $("levelQuizFeedback").textContent = passed ? "Level passed. Trophy unlocked." : "Try again later to unlock the next level.";
    try {
      const data = await api("/api/quiz/progress", {
        method: "POST",
        body: JSON.stringify({ level: levelQuizState.level, score, passed }),
      });
      state.player = data.player;
      saveSession();
      updateProfileUI();
    } catch {
    }
  }, 650);
}

$("skipQuizBtn").addEventListener("click", () => $("quizModal").classList.add("hidden"));

function animateStats() {
  for (const element of document.querySelectorAll(".stat-number")) {
    if (element.dataset.done === "true") continue;
    element.dataset.done = "true";
    const target = Number(element.dataset.countTarget || "0");
    const duration = 1100;
    const start = performance.now();

    function tick(now) {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      element.textContent = Math.round(target * eased).toLocaleString();
      if (progress < 1) window.requestAnimationFrame(tick);
    }

    window.requestAnimationFrame(tick);
  }
}

function startFactCarousel() {
  let factIndex = 0;
  const dots = $("factDots");
  dots.innerHTML = "";
  for (let i = 0; i < chessFacts.length; i++) {
    const dot = document.createElement("span");
    dots.appendChild(dot);
  }

  function showFact() {
    $("factText").classList.remove("fact-visible");
    window.setTimeout(() => {
      $("factText").textContent = chessFacts[factIndex];
      for (const [index, dot] of dots.querySelectorAll("span").entries()) {
        dot.classList.toggle("active", index === factIndex);
      }
      $("factText").classList.add("fact-visible");
      factIndex = (factIndex + 1) % chessFacts.length;
    }, 160);
  }

  showFact();
  window.setInterval(showFact, 5600);
}

function observeScrollReveals() {
  const revealElements = document.querySelectorAll(".reveal-on-scroll");
  if (!("IntersectionObserver" in window)) {
    for (const element of revealElements) element.classList.add("in-view");
    animateStats();
    return;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        entry.target.classList.add("in-view");
        if (entry.target.classList.contains("stats-panel")) animateStats();
        observer.unobserve(entry.target);
      }
    },
    { threshold: 0.2 },
  );

  for (const element of revealElements) observer.observe(element);
}

checkServer();
showPanels();
renderBoard();
enhanceButtons();
renderQuiz();
startFactCarousel();
observeScrollReveals();
startPolling();
