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
                sans: ['Inter', 'Segoe UI', 'Roboto', 'system-ui', 'sans-serif'],
                mono: ['JetBrains Mono', 'Consolas', 'monospace'],
            },
            colors: {
                brand: {
                    black: '#0B0B0B',
                    green: '#00C853',
                    blue: '#1E88E5',
                    white: '#FFFFFF',
                },
                primary: {
                    DEFAULT: '#1E88E5',
                    light: '#42A5F5',
                    dark: '#1565C0',
                    hover: '#1976D2',
                    foreground: '#FFFFFF',
                },
                success: {
                    DEFAULT: '#00C853',
                    light: '#00E676',
                    dark: '#00A844',
                    foreground: '#FFFFFF',
                },
                danger: {
                    DEFAULT: '#DC3545',
                    light: '#E74C3C',
                    dark: '#C82333',
                    foreground: '#FFFFFF',
                },
                warning: {
                    DEFAULT: '#FFC107',
                    light: '#FFD54F',
                    dark: '#FFA000',
                },
                neutral: {
                    DEFAULT: '#6C757D',
                },
                background: {
                    DEFAULT: '#FFFFFF',
                    secondary: '#F8F9FA',
                    card: '#FFFFFF',
                    hover: '#F1F3F5',
                },
                text: {
                    primary: '#212529',
                    secondary: '#6C757D',
                    muted: '#ADB5BD',
                    white: '#FFFFFF',
                },
                border: {
                    DEFAULT: '#DEE2E6',
                    light: '#E9ECEF',
                    dark: '#ADB5BD',
                },
                gray: {
                    50: '#F8F9FA',
                    100: '#E9ECEF',
                    200: '#DEE2E6',
                    300: '#CED4DA',
                    400: '#ADB5BD',
                    500: '#6C757D',
                    600: '#495057',
                    700: '#343A40',
                    800: '#212529',
                    900: '#0B0B0B',
                },
                // Shadcn compat (HSL variables)
                input: "hsl(var(--input))",
                ring: "hsl(var(--ring))",
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
                    from: { opacity: "0", transform: "translateY(10px)" },
                    to: { opacity: "1", transform: "translateY(0)" },
                },
            },
            animation: {
                "accordion-down": "accordion-down 0.2s ease-out",
                "accordion-up": "accordion-up 0.2s ease-out",
                "fade-in": "fade-in 0.5s ease-out",
                "slide-up": "slide-up 0.6s ease-out",
            },
            backgroundImage: {
                'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
                'financial-gradient': 'linear-gradient(135deg, #1E88E5 0%, #00C853 100%)',
            },
        },
    },
    plugins: [],
}
