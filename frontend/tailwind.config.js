/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      colors: {
        void: '#020213',
        cosmos: {
          950: '#04041a',
          900: '#07071e',
          800: '#0c0c28',
          700: '#111132',
          600: '#18183e',
          500: '#21214c',
          400: '#3a3a6a',
          300: '#5a5a90',
          200: '#8888b8',
          100: '#b8b8d8',
          50:  '#eeeeff',
        },
        nova: {
          blue:   '#4d8cff',
          violet: '#8b5cf6',
          cyan:   '#00c8d8',
          green:  '#00d4a0',
          red:    '#f0415e',
          amber:  '#f0a430',
        },
      },
    },
  },
  plugins: [],
}
