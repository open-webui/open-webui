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
        background: "var(--background)",
        foreground: "var(--foreground)",
        primaryRed: "#FF3D00",
        bgDark: "#000000",
        rose: "#FF8486",
        secondaryRed: "#CC1F1D",
        secondaryROse: "#FF0061",
      },
      fontFamily: {
        SpaceGrotesk: ["var(--font-space-grotesk)"],
        poppins: ["var(--font-poppins)"],
        urbanist: ["var(--font-urbanist)"],
        'sans': ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'Helvetica Neue', 'Arial', 'sans-serif'],
        'mono': ['Roboto Mono', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'Liberation Mono', 'Courier New', 'monospace'],
      },
      fontWeight: {
        normal: '400',
        medium: '500',
        semibold: '500',
        bold: '600',
      },
    },
  },
  plugins: [],
};
