/// <reference types="vite/client" />
// Fehlte bisher: ohne diese Referenz kennt TypeScript `import.meta.glob` und
// `import.meta.env` nicht. Gebraucht vom Emoji-Wächter (noEmoji.test.ts), der die
// Quelldateien über Vite einliest statt über `node:fs` — das würde sonst
// @types/node als Abhängigkeit erzwingen.
