/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{ts,tsx}",
    "../../packages/ui/**/*.{ts,tsx}",
    "!../../**/node_modules/**"
  ],
  theme: { extend: {} },
  plugins: []
}
