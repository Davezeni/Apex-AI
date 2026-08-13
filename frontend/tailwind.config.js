/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        surface: '#0f1115',
        panel: '#171a21',
        border: '#2a2f3a',
        accent: '#7c5cff',
      },
    },
  },
  plugins: [],
}
