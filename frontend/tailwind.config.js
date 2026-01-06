/** @type {import('tailwindcss').Config} */
export default {
    darkMode: ["class"],
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        container: {
            center: true,
            padding: "2rem",
            screens: {
                "2xl": "1400px",
            },
        },
        extend: {
            fontFamily: {
                sans: ['Sora', 'ui-sans-serif', 'system-ui', 'sans-serif'],
                mono: ['Space Mono', 'ui-monospace', 'SFMono-Regular', 'monospace'],
            },
            colors: {
                dark: {
                    950: '#0b0f1a',
                    900: '#121829',
                    800: '#181f32',
                    700: '#232c45',
                    600: '#2f3956',
                },
                primary: {
                    DEFAULT: '#2ad4c6',
                    light: '#63e0d5',
                    dark: '#1bb3a5',
                    hover: '#25c3b5',
                    dim: 'rgba(42, 212, 198, 0.12)',
                    foreground: '#000000',
                },
                accent: {
                    DEFAULT: '#f59f3a',
                    light: '#ffc36b',
                    dark: '#d27b15',
                    hover: '#de8a22',
                    dim: 'rgba(245, 159, 58, 0.12)',
                    foreground: '#1a1208',
                },
                success: '#2bd4a5',
                warning: '#f0b84b',
                danger: '#ff5a5f',
                info: '#4fc3f7',
                text: {
                    main: '#f8fafc',
                    muted: '#9aa3b2',
                    dim: '#6b7280',
                },
                border: "hsl(var(--border))",
                input: "hsl(var(--input))",
                ring: "hsl(var(--ring))",
                background: "hsl(var(--background))",
                foreground: "hsl(var(--foreground))",
                secondary: {
                    DEFAULT: "hsl(var(--secondary))",
                    foreground: "hsl(var(--secondary-foreground))",
                },
                destructive: {
                    DEFAULT: "hsl(var(--destructive))",
                    foreground: "hsl(var(--destructive-foreground))",
                },
                muted: {
                    DEFAULT: "hsl(var(--muted))",
                    foreground: "hsl(var(--muted-foreground))",
                },
                popover: {
                    DEFAULT: "hsl(var(--popover))",
                    foreground: "hsl(var(--popover-foreground))",
                },
                card: {
                    DEFAULT: "hsl(var(--card))",
                    foreground: "hsl(var(--card-foreground))",
                },
            },
            borderRadius: {
                lg: "var(--radius)",
                md: "calc(var(--radius) - 2px)",
                sm: "calc(var(--radius) - 4px)",
            },
            keyframes: {
                "accordion-down": {
                    from: { height: "0" },
                    to: { height: "var(--radix-accordion-content-height)" },
                },
                "accordion-up": {
                    from: { height: "var(--radix-accordion-content-height)" },
                    to: { height: "0" },
                },
                "fade-in": {
                    from: { opacity: "0" },
                    to: { opacity: "1" },
                },
                "slide-up": {
                    from: { opacity: "0", transform: "translateY(20px)" },
                    to: { opacity: "1", transform: "translateY(0)" },
                },
                "glow-pulse": {
                    "0%, 100%": { boxShadow: "0 0 15px rgba(0, 240, 255, 0.3), 0 0 30px rgba(0, 240, 255, 0.1)" },
                    "50%": { boxShadow: "0 0 25px rgba(0, 240, 255, 0.5), 0 0 50px rgba(0, 240, 255, 0.2)" },
                },
            },
            animation: {
                "accordion-down": "accordion-down 0.2s ease-out",
                "accordion-up": "accordion-up 0.2s ease-out",
                "fade-in": "fade-in 0.5s ease-out",
                "slide-up": "slide-up 0.6s ease-out",
                "glow-pulse": "glow-pulse 2s ease-in-out infinite",
            },
            backgroundImage: {
                'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
                'gradient-cyber': 'linear-gradient(135deg, #f59f3a 0%, #2ad4c6 100%)',
                'gradient-primary': 'linear-gradient(135deg, #2ad4c6 0%, #f59f3a 100%)',
            },
        },
    },
    plugins: [],
}
