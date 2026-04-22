/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#f4efe6",
        ink: "#12212f",
        accent: "#0f766e",
        ember: "#c2410c",
        mist: "#d8e8e4",
        shell: "#fffaf2",
      },
      boxShadow: {
        panel: "0 24px 60px rgba(18, 33, 47, 0.12)",
      },
      backgroundImage: {
        "hero-glow":
          "radial-gradient(circle at top left, rgba(15,118,110,0.18), transparent 38%), radial-gradient(circle at top right, rgba(194,65,12,0.16), transparent 32%)",
      },
    },
  },
  plugins: [],
};

