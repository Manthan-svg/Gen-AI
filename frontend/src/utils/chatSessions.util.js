export function normalizeUsername(username) {
  return String(username ?? '').trim();
}

function storageKey(username) {
  const u = normalizeUsername(username);
  return u ? `dc_chat_sessions_${u}` : '';
}

function activeKey(username) {
  const u = normalizeUsername(username);
  return u ? `dc_active_chat_${u}` : '';
}

function migrateLegacyKeys(rawUsername) {
  const raw = String(rawUsername ?? '');
  const normalized = normalizeUsername(rawUsername);
  if (!normalized) return;

  const legacySessionsKey = `dc_chat_sessions_${raw}`;
  const legacyActiveKey = `dc_active_chat_${raw}`;
  const nextSessionsKey = `dc_chat_sessions_${normalized}`;
  const nextActiveKey = `dc_active_chat_${normalized}`;

  if (raw && raw !== normalized) {
    const legacySessions = localStorage.getItem(legacySessionsKey);
    if (legacySessions && !localStorage.getItem(nextSessionsKey)) {
      localStorage.setItem(nextSessionsKey, legacySessions);
    }

    const legacyActive = localStorage.getItem(legacyActiveKey);
    if (legacyActive && !localStorage.getItem(nextActiveKey)) {
      localStorage.setItem(nextActiveKey, legacyActive);
    }
  }

  // Also scan for any keys with trailing/leading spaces and migrate them.
  for (let i = 0; i < localStorage.length; i += 1) {
    const key = localStorage.key(i);
    if (!key) continue;

    if (key.startsWith('dc_chat_sessions_')) {
      const suffix = key.slice('dc_chat_sessions_'.length);
      if (suffix && suffix !== normalized && suffix.trim() === normalized) {
        const value = localStorage.getItem(key);
        if (value && !localStorage.getItem(nextSessionsKey)) {
          localStorage.setItem(nextSessionsKey, value);
        }
      }
    }

    if (key.startsWith('dc_active_chat_')) {
      const suffix = key.slice('dc_active_chat_'.length);
      if (suffix && suffix !== normalized && suffix.trim() === normalized) {
        const value = localStorage.getItem(key);
        if (value && !localStorage.getItem(nextActiveKey)) {
          localStorage.setItem(nextActiveKey, value);
        }
      }
    }
  }
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
  migrateLegacyKeys(username);
  const key = storageKey(username);
  if (!key) return [];
  const raw = localStorage.getItem(key);
  const parsed = safeJsonParse(raw, []);
  return Array.isArray(parsed) ? parsed : [];
}

export function saveChatSessions(username, sessions) {
  if (!username) return;
  migrateLegacyKeys(username);
  const key = storageKey(username);
  if (!key) return;
  localStorage.setItem(key, JSON.stringify(sessions ?? []));
}

export function ensureInitialChatSession(username) {
  if (!username) return { sessions: [], activeSessionId: null };
  migrateLegacyKeys(username);

  let sessions = getChatSessions(username);
  if (sessions.length === 0) {
    // Preserve existing backend history for older users.
    sessions = [
      {
        id: 'legacy',
        sessionId: `session_${normalizeUsername(username)}`,
        title: 'Chat 1',
        createdAt: nowIso(),
        lastMessageAt: null,
        lastMessagePreview: '',
      },
    ];
    saveChatSessions(username, sessions);
    const akey = activeKey(username);
    if (akey) localStorage.setItem(akey, sessions[0].sessionId);
  }

  const active = getActiveChatSessionId(username) ?? sessions[0]?.sessionId ?? null;
  const akey = activeKey(username);
  if (active && akey) localStorage.setItem(akey, active);

  return { sessions, activeSessionId: active };
}

export function createNewChatSession(username) {
  if (!username) return null;
  migrateLegacyKeys(username);

  const id = genId();
  const sessionId = `session_${normalizeUsername(username)}_${id}`;

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
  const akey = activeKey(username);
  if (akey) localStorage.setItem(akey, sessionId);

  return newSession;
}

export function getActiveChatSessionId(username) {
  if (!username) return null;
  const key = activeKey(username);
  if (!key) return null;
  return localStorage.getItem(key);
}

export function setActiveChatSessionId(username, sessionId) {
  if (!username || !sessionId) return;
  const key = activeKey(username);
  if (!key) return;
  localStorage.setItem(key, sessionId);
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
