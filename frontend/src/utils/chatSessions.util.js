import api from './api.util';

export function normalizeUsername(username) {
  return String(username ?? '').trim();
}

function genId() {
  return `${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

export async function getChatSessions() {
  const res = await api.get('/chat-sessions');
  const sessions = res?.data?.sessions;
  return Array.isArray(sessions) ? sessions : [];
}

export async function ensureInitialChatSession(username) {
  const sessions = await getChatSessions();
  if (sessions.length > 0) {
    return {
      sessions,
      activeSessionId: sessions[0]?.sessionId ?? null,
    };
  }

  const sessionId = `session_${normalizeUsername(username)}`;
  const session = await createChatSession(sessionId, 'Chat 1');
  return {
    sessions: session ? [session] : [],
    activeSessionId: session?.sessionId ?? null,
  };
}

export async function createNewChatSession(username) {
  const sessions = await getChatSessions();
  const nextNum = sessions.length + 1;
  const sessionId = `session_${normalizeUsername(username)}_${genId()}`;
  return createChatSession(sessionId, `Chat ${nextNum}`);
}

async function createChatSession(sessionId, title) {
  const res = await api.post('/chat-sessions', {
    sessionId,
    title,
  });
  return res?.data?.session ?? null;
}

export async function touchChatSession(sessionId, patch) {
  const res = await api.patch(`/chat-sessions/${sessionId}`, patch);
  return res?.data?.session ?? null;
}

export async function maybeSetChatTitleFromFirstMessage(sessionId, humanText) {
  const sessions = await getChatSessions();
  const session = sessions.find((s) => s.sessionId === sessionId);
  if (!session) return null;

  const alreadyCustomized =
    session.title && !/^Chat\s+\d+$/.test(String(session.title).trim()) && session.title !== 'Chat 1';
  if (alreadyCustomized) return session;

  const t = String(humanText ?? '').trim();
  if (!t) return session;
  const title = t.length > 28 ? `${t.slice(0, 28)}…` : t;

  return touchChatSession(sessionId, { title });
}
