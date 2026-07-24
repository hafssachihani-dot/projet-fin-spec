import { createClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

export const isSupabaseConfigured = Boolean(supabaseUrl && supabaseAnonKey);

export const supabase = isSupabaseConfigured
  ? createClient(supabaseUrl, supabaseAnonKey, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
      },
    })
  : null;

export function isAuthSessionError(error) {
  const value = `${error?.code || ""} ${error?.message || error || ""}`;
  return /session_not_found|invalid refresh token|refresh token not found|bad_jwt|jwt.*expired|token.*expired/i.test(value);
}

export async function clearLocalSession() {
  if (!supabase) return;
  await supabase.auth.signOut({ scope: "local" }).catch(() => {});
}

function expiredSessionError() {
  const error = new Error("Ta session a expire. Reconnecte-toi pour continuer.");
  error.code = "AUTH_SESSION_EXPIRED";
  return error;
}

export async function getCurrentSession() {
  if (!supabase) return null;
  const { data, error } = await supabase.auth.getSession();
  if (error) {
    if (isAuthSessionError(error)) {
      await clearLocalSession();
      return null;
    }
    throw error;
  }
  return data.session;
}

export async function refreshCurrentSession() {
  if (!supabase) return null;

  const currentSession = await getCurrentSession();
  if (!currentSession) return null;

  const expiresAt = Number(currentSession?.expires_at || 0);
  const isStillValid = expiresAt > Math.floor(Date.now() / 1000) + 60;

  // Supabase refreshes sessions automatically. Avoid requiring a refresh token
  // when the current access token is still valid, but confirm that its server
  // session has not been revoked.
  if (currentSession?.access_token && isStillValid) {
    const { error: userError } = await supabase.auth.getUser();
    if (userError) {
      if (isAuthSessionError(userError)) {
        await clearLocalSession();
        throw expiredSessionError();
      }
      throw userError;
    }
    return currentSession;
  }

  if (!currentSession.refresh_token) {
    await clearLocalSession();
    throw expiredSessionError();
  }

  const { data, error } = await supabase.auth.refreshSession();
  if (error) {
    if (isAuthSessionError(error)) {
      await clearLocalSession();
      throw expiredSessionError();
    }
    throw error;
  }
  return data.session;
}

export async function getCurrentProfile(userId) {
  if (!supabase) return null;
  const { data, error } = await supabase
    .from("profiles")
    .select("id, full_name, role, study_level")
    .eq("id", userId)
    .maybeSingle();

  if (error) throw error;
  return data;
}

export async function signInWithPassword(email, password) {
  const { data, error } = await supabase.auth.signInWithPassword({ email, password });
  if (error) throw error;
  return data;
}

export async function signOut() {
  const { error } = await supabase.auth.signOut();
  if (error) {
    if (isAuthSessionError(error)) {
      await clearLocalSession();
      return;
    }
    throw error;
  }
}
