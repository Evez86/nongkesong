import React, { useEffect, useRef } from 'react';

const WIDTH = 150;
const HEIGHT = 115;
const DURATION = 1450;

function arc(start, lift, end, progress) {
  const remaining = 1 - progress;
  return start * remaining ** 2 + 2 * lift * remaining * progress + end * progress ** 2;
}

function drawPage(ctx, progress) {
  const t = progress * progress * (3 - 2 * progress);
  const topX = arc(141, 118, 15, t);
  const topY = arc(75, -16, 26, t);
  const edgeX = arc(52, 70, 10, t);
  const edgeY = arc(102, 51, 103, t);
  const curl = Math.sin(t * Math.PI);

  ctx.clearRect(0, 0, WIDTH, HEIGHT);
  ctx.globalAlpha = Math.min(t * 10, 1, (1 - t) * 9);
  const paper = ctx.createLinearGradient(13, 102, topX + 8, topY - 5);
  paper.addColorStop(0, '#b47d48');
  paper.addColorStop(0.42, '#efc088');
  paper.addColorStop(0.78, '#f5d09d');
  paper.addColorStop(1, '#e1aa73');
  ctx.fillStyle = paper;
  ctx.strokeStyle = '#69432f';
  ctx.lineWidth = 1.15;
  ctx.lineJoin = 'round';
  ctx.beginPath();
  ctx.moveTo(9, 106);
  ctx.quadraticCurveTo(31, 90, 69, 77);
  ctx.quadraticCurveTo((69 + topX) / 2 + 3, (77 + topY) / 2 - 7 * curl, topX, topY);
  ctx.bezierCurveTo(topX + 5 * curl, topY + 19, edgeX + 10 * curl, edgeY - 24, edgeX, edgeY);
  ctx.quadraticCurveTo((edgeX + 9) / 2, edgeY - 5 * curl, 9, 106);
  ctx.closePath();
  ctx.fill();
  ctx.stroke();
  ctx.globalAlpha = 1;
}

export function ReadingPageTurn() {
  const canvas = useRef(null);

  useEffect(() => {
    const context = canvas.current.getContext('2d');
    if (!context) return;

    const motionPreference = window.matchMedia('(prefers-reduced-motion: reduce)');
    let frame;
    let timer;

    function play() {
      if (motionPreference.matches) return;
      let start;

      function step(time) {
        start ??= time;
        const progress = Math.min((time - start) / DURATION, 1);
        drawPage(context, progress);

        if (progress < 1) {
          frame = window.requestAnimationFrame(step);
        } else {
          context.clearRect(0, 0, WIDTH, HEIGHT);
          timer = window.setTimeout(play, 4300);
        }
      }

      frame = window.requestAnimationFrame(step);
    }

    function reset() {
      window.clearTimeout(timer);
      window.cancelAnimationFrame(frame);
      context.clearRect(0, 0, WIDTH, HEIGHT);
      if (!motionPreference.matches && !document.hidden) {
        timer = window.setTimeout(play, 850);
      }
    }

    reset();
    motionPreference.addEventListener('change', reset);
    document.addEventListener('visibilitychange', reset);
    return () => {
      motionPreference.removeEventListener('change', reset);
      document.removeEventListener('visibilitychange', reset);
      window.clearTimeout(timer);
      window.cancelAnimationFrame(frame);
    };
  }, []);

  return <canvas className="reading-page-turn" ref={canvas} width={WIDTH} height={HEIGHT} aria-hidden="true" />;
}
