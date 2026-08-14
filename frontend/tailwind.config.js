/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Warm monochrome dark theme (matched to reference screenshots).
        surface: '#34302D',   // main content background
        panel: '#252523',     // raised panels / sidebar
        deep: '#17130A',      // deepest sidebar / nav
        ink: '#070707',       // near-black
        border: '#3B342A',    // borders / dividers
        muted: '#8A8884',     // secondary text (warm gray)
        fg: '#E8E6E1',        // primary text (warm white)
        accent: '#6b6660',    // subtle warm accent (send button), monochrome
      },
      borderRadius: {
        xl: '10px',
        '2xl': '14px',
      },
    },
  },
  plugins: [],
}
