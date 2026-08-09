import type { MetadataRoute } from 'next';

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: 'Pegasus Race Intelligence',
    short_name: 'Pegasus',
    description: 'Official race program, data freshness and transparent performance tracking.',
    start_url: '/command-center',
    display: 'standalone',
    background_color: '#061725',
    theme_color: '#061725',
    icons: [{ src: '/icon.svg', sizes: 'any', type: 'image/svg+xml', purpose: 'any' }]
  };
}