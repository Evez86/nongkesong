import React from 'react';
import sheet from '../assets/journal-stickers.webp';

const SHEET_WIDTH = 1536;
const SHEET_HEIGHT = 1024;

export function Sticker({ region: [x, y, width, height], source = sheet, className = '' }) {
  return (
    <span className={`sticker-space ${className}`} aria-hidden="true">
      <span className="sticker" style={{
        aspectRatio: `${width} / ${height}`,
        inlineSize: `var(--sticker-inline-size, ${Math.min(100, 88 * width / height)}%)`,
        backgroundImage: `url(${source})`,
        backgroundSize: `${SHEET_WIDTH / width * 100}% ${SHEET_HEIGHT / height * 100}%`,
        backgroundPosition: `${x / (SHEET_WIDTH - width) * 100}% ${y / (SHEET_HEIGHT - height) * 100}%`,
      }} />
    </span>
  );
}
