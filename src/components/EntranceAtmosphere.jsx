import React from 'react';

const panes = ['left-upper', 'left-lower', 'right'];
const drops = Array.from({ length: 14 }, (_, index) => {
  const duration = 1.45 + (index % 6) * 0.17;
  return {
    '--drop-x': `${((index * 29 + 5) % 97)}%`,
    '--drop-length': `${1.1 + (index % 4) * 0.46}cqw`,
    '--drop-duration': `${duration}s`,
    '--drop-delay': `${-(index * 0.38 % duration)}s`,
  };
});

export function EntranceAtmosphere({ source }) {
  return (
    <div className="entrance-atmosphere" aria-hidden="true">
      {panes.map((pane) => (
        <div className={`rain-pane rain-pane--${pane}`} key={pane}>
          {drops.map((style, index) => <i key={index} style={style} />)}
        </div>
      ))}
      <div className="coffee-steam entrance-steam"><i /><i /><i /></div>
      <div className="sleeping-cat entrance-cat">
        <img src={source} width="1858" height="846" alt="" />
      </div>
    </div>
  );
}
