import { defineConfig } from 'vitest/config'

// Unit tests for pure utilities — Node environment (no DOM needed).
export default defineConfig({
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts'],
  },
})
