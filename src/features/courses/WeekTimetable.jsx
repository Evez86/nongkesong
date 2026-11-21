import React from 'react';

export function WeekTimetable({ weekdays, periodCount, eveningStart, meetings }) {
  const periods = Array.from({ length: periodCount }, (_, index) => index + 1);

  return (
    <table className="course-week" aria-label="本学期周课表">
      <thead>
        <tr>
          <th scope="col">节次</th>
          {weekdays.map((day) => <th scope="col" key={day}>{day}</th>)}
        </tr>
      </thead>
      <tbody>
        {periods.map((period) => (
          <tr key={period} data-evening={period >= eveningStart || undefined}
            data-evening-start={period === eveningStart || undefined}>
            <th scope="row">
              {period}
              {period === eveningStart && <span className="course-week__evening-mark">晚间</span>}
            </th>
            {weekdays.map((day, column) => {
              const lastDay = column === weekdays.length - 1 || undefined;
              const meeting = meetings.find((item) =>
                item.day === column && period >= item.start && period <= item.end);
              if (!meeting) return <td key={day} data-last-day={lastDay} />;
              if (period !== meeting.start) return null;

              const span = meeting.end - meeting.start + 1;
              return (
                <td key={day} rowSpan={span} data-last-day={lastDay}>
                  <div className="course-meeting" data-tone={meeting.tone} style={{ '--period-span': span }}>
                    <strong>{meeting.title}</strong>
                    <span>{meeting.room}</span>
                  </div>
                </td>
              );
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
