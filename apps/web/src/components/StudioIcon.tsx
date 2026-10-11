type IconName = 'home' | 'projects' | 'characters' | 'story' | 'wardrobe' | 'shots' | 'review' | 'csp' | 'release' | 'integrations' | 'settings' | 'jobs'

const paths: Record<IconName, string> = {
  home: 'M3 10 12 3l9 7v10H15v-6H9v6H3Z',
  projects: 'M3 7V5h6l2 2h10v13H3Z',
  characters: 'M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0ZM4 21v-2a8 8 0 0 1 16 0v2',
  story: 'M4 4h6a3 3 0 0 1 3 3v14a5 5 0 0 0-5-3H4ZM13 7a3 3 0 0 1 3-3h5v14h-3a5 5 0 0 0-5 3',
  wardrobe: 'm8 3-5 4 3 4 2-2v12h8V9l2 2 3-4-5-4a4 4 0 0 1-8 0Z',
  shots: 'M3 6h5l2-3h4l2 3h5v14H3ZM16 13a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z',
  review: 'M3 4h18v16H3ZM7 12l3 3 7-7',
  csp: 'M4 3h11l5 5v13H4ZM15 3v6h5M8 14h8M8 17h5',
  release: 'M12 16V3m-5 5 5-5 5 5M4 14v7h16v-7',
  integrations: 'M9 3v5m6-5v5M6 8h12v3a6 6 0 0 1-12 0ZM12 17v4',
  settings: 'M12 8a4 4 0 1 1 0 8 4 4 0 0 1 0-8ZM12 2v3m0 14v3M2 12h3m14 0h3M5 5l2 2m10 10 2 2M5 19l2-2M17 7l2-2',
  jobs: 'M4 5h16M4 12h16M4 19h16M8 3v4m8 3v4m-6 3v4',
}

export function StudioIcon({ name }: { name: IconName }) {
  return <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]} /></svg>
}
