function storageKey(username) {
  return `dc_chat_sessions_${username}`;
}

function activeKey(username) {
  return `dc_active_chat_${username}`;
}

function safeJsonParse(value, fallback) {
  if (!value) return fallback;
  try {
    return JSON.parse(value);
  } catch {
    return fallback;
  }
}

function nowIso() {
  return new Date().toISOString();
}

function genId() {
  // Good enough for client-side session identifiers
  return `${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

export function getChatSessions(username) {
  if (!username) return [];
  const raw = localStorage.getItem(storageKey(username));
  const parsed = safeJsonParse(raw, []);
  return Array.isArray(parsed) ? parsed : [];
}

export function saveChatSessions(username, sessions) {
  if (!username) return;
  localStorage.setItem(storageKey(username), JSON.stringify(sessions ?? []));
}

export function ensureInitialChatSession(username) {
  if (!username) return { sessions: [], activeSessionId: null };

  let sessions = getChatSessions(username);
  if (sessions.length === 0) {
    // Preserve existing backend history for older users.
    sessions = [
      {
        id: 'legacy',
        sessionId: `session_${username}`,
        title: 'Chat 1',
        createdAt: nowIso(),
        lastMessageAt: null,
        lastMessagePreview: '',
      },
    ];
    saveChatSessions(username, sessions);
    localStorage.setItem(activeKey(username), sessions[0].sessionId);
  }

  const active = getActiveChatSessionId(username) ?? sessions[0]?.sessionId ?? null;
  if (active) localStorage.setItem(activeKey(username), active);

  return { sessions, activeSessionId: active };
}

export function createNewChatSession(username) {
  if (!username) return null;

  const id = genId();
  const sessionId = `session_${username}_${id}`;

  const sessions = getChatSessions(username);
  const nextNum = sessions.length + 1;
  const newSession = {
    id,
    sessionId,
    title: `Chat ${nextNum}`,
    createdAt: nowIso(),
    lastMessageAt: null,
    lastMessagePreview: '',
  };

  const updated = [newSession, ...sessions];
  saveChatSessions(username, updated);
  localStorage.setItem(activeKey(username), sessionId);

  return newSession;
}

export function getActiveChatSessionId(username) {
  if (!username) return null;
  return localStorage.getItem(activeKey(username));
}

export function setActiveChatSessionId(username, sessionId) {
  if (!username || !sessionId) return;
  localStorage.setItem(activeKey(username), sessionId);
}

export function touchChatSession(username, sessionId, patch) {
  if (!username || !sessionId) return;
  const sessions = getChatSessions(username);
  const updated = sessions.map((s) =>
    s.sessionId === sessionId
      ? {
          ...s,
          ...patch,
        }
      : s
  );
  saveChatSessions(username, updated);
}

export function maybeSetChatTitleFromFirstMessage(username, sessionId, humanText) {
  if (!username || !sessionId) return;
  const sessions = getChatSessions(username);
  const session = sessions.find((s) => s.sessionId === sessionId);
  if (!session) return;

  const alreadyCustomized =
    session.title && !/^Chat\s+\d+$/.test(String(session.title).trim()) && session.title !== 'Chat 1';
  if (alreadyCustomized) return;

  const t = String(humanText ?? '').trim();
  if (!t) return;
  const title = t.length > 28 ? `${t.slice(0, 28)}…` : t;

  touchChatSession(username, sessionId, { title });
}

