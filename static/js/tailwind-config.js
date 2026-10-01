/* Tailwind CDN configuration — DNA Lab Pakistan
   Loaded in base.html after the Tailwind CDN script. */
tailwind.config = {
  theme: {
    extend: {
      colors: {
        /* Core brand — derived from the original #025468 */
        ink: '#063B49',          // headings, body text
        'ink-soft': '#4A6B74',   // secondary text
        teal: {
          DEFAULT: '#0A6B80',    // primary actions, links
          dark: '#063B49',
          light: '#128CA6',
          wash: '#E8F1F3',       // tinted panels
        },
        /* Kept for backwards compatibility with existing markup */
        phthalo: {
          DEFAULT: '#0A6B80',
          light: '#128CA6',
          dark: '#063B49',
        },
        amber: {
          DEFAULT: '#D98A14',    // route markers, status — used sparingly
          soft: '#FBF2E2',
        },
        paper: '#F5F8F8',
        line: '#DAE4E6',
        danger: '#9B2C2C',
      },
      fontFamily: {
        serif: ['Newsreader', 'Georgia', 'serif'],
        sans: ['"Public Sans"', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
        /* legacy alias used by older templates */
        inter: ['"Public Sans"', 'system-ui', 'sans-serif'],
      },
      maxWidth: {
        measure: '68ch',
      },
      borderRadius: {
        DEFAULT: '4px',
        card: '6px',
      },
    },
  },
};