/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Light Studio Palette (Default)
        lightBg: '#f8fafc',
        lightSurface: '#ffffff',
        lightBorder: '#e2e8f0',
        lightMuted: '#64748b',

        // Dark Studio Palette
        darkBg: '#0b0f17',
        darkSurface: '#131b2a',
        darkBorder: '#1e293b',
        darkMuted: '#94a3b8',

        // Refined Accent Accents
        primaryIndigo: '#4f46e5',
        primaryCyan: '#06b6d4',
        accentCoral: '#f43f5e',
        accentAmber: '#d97706',
        accentEmerald: '#059669',
      }
    },
  },
  plugins: [],
}