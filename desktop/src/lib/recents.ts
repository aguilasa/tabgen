// Opened songs: audio probing (Rust `probe_audio`, ffprobe) and the recents
// list persisted in the webview's localStorage.
import { invoke } from "@tauri-apps/api/core";

export const AUDIO_EXTENSIONS = ["mp3", "wav", "flac"] as const;

export interface AudioInfo {
  duration_s: number;
  /** ffprobe container name (mp3, wav, flac). */
  format: string;
  sample_rate: number | null;
  channels: number | null;
}

/** One opened song; the workspace (UI-TASK-04) fills processed_at/artifacts. */
export interface RecentEntry {
  path: string;
  name: string;
  duration_s: number;
  format: string;
  sample_rate: number | null;
  channels: number | null;
  /** ISO timestamp of the last time the song was opened. */
  opened_at: string;
  /** ISO timestamp of the last finished pipeline run; null = not processed. */
  processed_at: string | null;
  /** Artifacts/cache present for the song (e.g. "stems", "análise", "tab"). */
  artifacts: string[];
}

const KEY = "tabgen.recents";
const MAX_RECENTS = 20;

export function baseName(path: string): string {
  return path.split(/[\\/]/).pop() ?? path;
}

export function extensionOf(path: string): string {
  const name = baseName(path);
  const dot = name.lastIndexOf(".");
  return dot > 0 ? name.slice(dot + 1).toLowerCase() : "";
}

export function isSupportedAudio(path: string): boolean {
  return (AUDIO_EXTENSIONS as readonly string[]).includes(extensionOf(path));
}

export function probeAudio(path: string): Promise<AudioInfo> {
  return invoke<AudioInfo>("probe_audio", { path });
}

export function fileExists(path: string): Promise<boolean> {
  return invoke<boolean>("file_exists", { path });
}

/** Dev-only path from TABGEN_OPEN, handed out once per app run. */
export function startupOpen(): Promise<string | null> {
  return invoke<string | null>("startup_open");
}

export function loadRecents(): RecentEntry[] {
  try {
    const stored: unknown = JSON.parse(localStorage.getItem(KEY) ?? "[]");
    return Array.isArray(stored) ? (stored as RecentEntry[]) : [];
  } catch {
    return [];
  }
}

function saveRecents(entries: RecentEntry[]): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(entries));
  } catch {
    // storage unavailable: the list stays for this session only
  }
}

/** Put `entry` first (replacing an older entry for the same path) and persist. */
export function rememberRecent(entry: RecentEntry): RecentEntry[] {
  const previous = loadRecents().find((e) => e.path === entry.path);
  const merged: RecentEntry = previous
    ? { ...entry, processed_at: previous.processed_at, artifacts: previous.artifacts }
    : entry;
  const next = [merged, ...loadRecents().filter((e) => e.path !== entry.path)].slice(
    0,
    MAX_RECENTS,
  );
  saveRecents(next);
  return next;
}

/**
 * Record a finished pipeline run for the entry with `path` (kept in place):
 * processed_at = now, artifacts replaced. Returns the persisted list; an
 * unknown path leaves it unchanged.
 */
export function markProcessed(path: string, artifacts: string[]): RecentEntry[] {
  const entries = loadRecents();
  const next = entries.map((e) =>
    e.path === path ? { ...e, processed_at: new Date().toISOString(), artifacts } : e,
  );
  if (next.some((e) => e.path === path)) saveRecents(next);
  return next;
}

/** Drop entries whose file no longer exists; persist and return the rest. */
export async function pruneRecents(): Promise<RecentEntry[]> {
  const entries = loadRecents();
  const exists = await Promise.all(entries.map((e) => fileExists(e.path).catch(() => true)));
  const gone = new Set(entries.filter((_, i) => !exists[i]).map((e) => e.path));
  // re-read: an entry added while checking must not be lost
  const current = loadRecents().filter((e) => !gone.has(e.path));
  if (gone.size > 0) saveRecents(current);
  return current;
}

export function formatDuration(seconds: number): string {
  const total = Math.round(seconds);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = String(total % 60).padStart(2, "0");
  return h > 0 ? `${h}:${String(m).padStart(2, "0")}:${s}` : `${m}:${s}`;
}

export function formatAudio(entry: Pick<RecentEntry, "format" | "sample_rate" | "channels">): string {
  const parts = [entry.format.split(",")[0].toUpperCase()];
  if (entry.sample_rate) parts.push(`${(entry.sample_rate / 1000).toLocaleString("pt-BR")} kHz`);
  if (entry.channels === 1) parts.push("mono");
  else if (entry.channels === 2) parts.push("estéreo");
  else if (entry.channels) parts.push(`${entry.channels} canais`);
  return parts.join(" · ");
}

/** "há 5 min", "ontem", "12/10/2026"… */
export function formatWhen(iso: string, now = new Date()): string {
  const then = new Date(iso);
  const minutes = Math.floor((now.getTime() - then.getTime()) / 60000);
  if (minutes < 1) return "agora há pouco";
  if (minutes < 60) return `há ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `há ${hours} h`;
  const days = Math.floor(hours / 24);
  if (days === 1) return "ontem";
  if (days < 7) return `há ${days} dias`;
  return then.toLocaleDateString("pt-BR");
}
