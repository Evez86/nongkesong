import React, { useLayoutEffect, useRef } from 'react';
import { MAP_HEIGHT, MAP_WIDTH, stages } from './roadmapStages.js';

export function MapRoute() {
  const canvas = useRef(null);

  useLayoutEffect(() => {
    const ctx = canvas.current?.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, MAP_WIDTH, MAP_HEIGHT);
    ctx.beginPath();
    ctx.moveTo(stages[0].x, stages[0].y);

    for (let index = 1; index < stages.length; index += 1) {
      const previous = stages[index - 1];
      const current = stages[index];
      const midX = (previous.x + current.x) / 2;
      ctx.bezierCurveTo(midX, previous.y, midX, current.y, current.x, current.y);
    }

    ctx.lineCap = 'round';
    ctx.setLineDash([8, 12]);
    ctx.strokeStyle = '#f8e6b9b3';
    ctx.lineWidth = 7;
    ctx.stroke();
    ctx.strokeStyle = '#995c42';
    ctx.lineWidth = 3;
    ctx.stroke();
  }, []);

  return <canvas className="roadmap-path" ref={canvas} width={MAP_WIDTH} height={MAP_HEIGHT} aria-hidden="true" />;
}
