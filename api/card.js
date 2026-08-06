// Vercel Serverless Function: api/card.js
// Renders the animated Cyberpunk Terminal Card for Ayush Singh (Ayush-840) dynamically

import fs from 'fs';
import path from 'path';

export default function handler(req, res) {
  res.setHeader('Content-Type', 'image/svg+xml');
  res.setHeader('Cache-Control', 'public, max-age=7200, s-maxage=7200, stale-while-revalidate=86400');
  
  try {
    const bannerPath = path.join(process.cwd(), 'assets', 'banner.svg');
    const svgData = fs.readFileSync(bannerPath, 'utf8');
    return res.status(200).send(svgData);
  } catch (error) {
    return res.status(500).send(`<svg xmlns="http://www.w3.org/2000/svg" width="400" height="100"><text x="10" y="50" fill="red">Error loading card</text></svg>`);
  }
}
