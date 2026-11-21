// Example data for the static preview. The school determines the real periods and graduation requirements.
export const creditCategories = [
  { name: '公共必修', earned: 34, required: 42 },
  { name: '专业必修', earned: 36, required: 58 },
  { name: '选修课', earned: 14, required: 32 },
  { name: '实践学分', earned: 8, required: 28 },
];

export const selectedTerm = 4;
export const semesters = ['大一上', '大一下', '大二上', '大二下', '大三上', '大三下', '大四上', '大四下'];

export const timetable = {
  termCredits: 13,
  weekdays: ['周一', '周二', '周三', '周四', '周五'],
  periodCount: 12,
  eveningStart: 9,
  meetings: [
    { day: 0, start: 1, end: 2, title: '数据分析', room: '教A203', tone: 'oak' },
    { day: 2, start: 1, end: 2, title: '专业英语', room: '教B104', tone: 'birch' },
    { day: 1, start: 3, end: 4, title: '数据库', room: '教A306', tone: 'clay' },
    { day: 4, start: 3, end: 4, title: '学术写作', room: '教B202', tone: 'honey' },
    { day: 0, start: 5, end: 6, title: '数据库', room: '机房 2', tone: 'clay' },
    { day: 3, start: 6, end: 7, title: '科研实践', room: '实验楼', tone: 'oak' },
    { day: 2, start: 7, end: 8, title: '数据分析', room: '机房 1', tone: 'oak' },
    { day: 3, start: 9, end: 10, title: '科研实践', room: '实验楼', tone: 'oak' },
    { day: 1, start: 11, end: 11, title: '专业英语', room: '教B104', tone: 'birch' },
  ],
};
