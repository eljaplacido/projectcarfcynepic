/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                primary: '#7C3AED',
                'primary-light': '#A78BFA',
                accent: '#10B981',
                'accent-light': '#34D399',
                'cynefin-clear': '#10B981',
                'cynefin-complicated': '#3B82F6',
                'cynefin-complex': '#8B5CF6',
                'cynefin-chaotic': '#EF4444',
                'cynefin-disorder': '#6B7280',
                'confidence-high': '#10B981',
                'confidence-medium': '#F59E0B',
                'confidence-low': '#EF4444',
            },
            fontFamily: {
                sans: ['Inter', 'system-ui', 'sans-serif'],
            },
            backdropBlur: {
                xs: '2px',
            },
        },
    },
    plugins: [],
}
