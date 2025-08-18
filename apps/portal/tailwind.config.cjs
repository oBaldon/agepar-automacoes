/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{ts,tsx}",
    "./node_modules/@agepar/ui/dist/**/*.{js,jsx}",
  ],
  theme: { extend: {} },
  plugins: [],
}
