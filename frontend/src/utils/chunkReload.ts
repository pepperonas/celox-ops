/**
 * Nach einem Deploy referenziert ein offener Tab noch alte Chunk-Hashes (die der
 * Server nicht mehr hat / während des Rebuild-Fensters 502t). Ein einmaliger Reload
 * pro Cooldown-Fenster holt das frische Bundle — der Cooldown verhindert eine
 * Reload-Schleife, falls der Server länger nicht erreichbar ist. Rein & testbar.
 */
export const CHUNK_RELOAD_COOLDOWN_MS = 30_000

export function shouldReloadOnChunkError(
  now: number,
  lastReloadAt: number,
  cooldownMs: number = CHUNK_RELOAD_COOLDOWN_MS,
): boolean {
  return now - lastReloadAt > cooldownMs
}
