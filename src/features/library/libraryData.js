export const libraryTabs = [
  ['all', '全部'],
  ['course', '课程介绍'],
  ['teacher', '开课教师'],
  ['experience', '学习经验'],
  ['exam', '历年真题'],
];

export const initialCourseQuery = '概率论与数理统计';

export const courses = [
  {
    id: 'probability', name: initialCourseQuery, aliases: ['概率论', '概率统计', '数理统计', '概率'],
    summary: '学习随机变量、常见分布、参数估计与假设检验。',
    prerequisites: '高等数学',
    topics: ['随机事件与概率', '随机变量及其分布', '大数定律和中心极限定理', '参数估计与假设检验'],
    teachers: [
      { id: 'class-01', name: '任课教师 A', className: '教学班 01', term: '2026–2027 学年第一学期', department: '数学与统计学院' },
      { id: 'class-02', name: '任课教师 B', className: '教学班 02', term: '2026–2027 学年第一学期', department: '数学与统计学院' },
      { id: 'class-03', name: '任课教师 C', className: '教学班 01', term: '2025–2026 学年第二学期', department: '数学与统计学院' },
    ],
    experiences: [
      {
        id: 'common-distributions', title: '从例题开始整理常见分布',
        summary: '按章节记录公式与适用条件，再用错题检查理解。',
        tips: [
          '学完一种分布，先写下它解决的问题和适用条件，再做一道例题检查自己能否选对模型。',
          '把容易混淆的分布写在同一张纸上。复习时先看题干，写出选择依据，再查公式。',
          '整理错题时区分选错模型、漏掉条件和计算失误，优先重做前两类。',
        ],
      },
    ],
    exams: [
      {
        id: 'final-2025-1', year: '2025–2026', term: '第一学期', type: '期末',
        format: 'PDF', answers: false, provider: '校内课程平台', access: 'campus_login',
        availability: 'unverified',
      },
      {
        id: 'final-2024-2', year: '2024–2025', term: '第二学期', type: '期末',
        format: 'PDF', answers: true, provider: '院系共享资料', availability: 'unverified',
      },
      {
        id: 'midterm-2024-1', year: '2024–2025', term: '第一学期', type: '期中',
        availability: 'unavailable',
      },
    ],
  },
  {
    id: 'calculus', name: '高等数学', aliases: ['高数', '微积分', '高等数学A', '高等数学B'],
    summary: '学习极限、连续、微分积分和常微分方程等基础知识。',
    prerequisites: '高中数学',
    topics: ['函数与极限', '一元函数微分学', '一元函数积分学', '常微分方程'],
    teachers: [
      { id: 'class-01', name: '任课教师 A', className: '教学班 01', term: '2026–2027 学年第一学期', department: '数学与统计学院' },
    ],
    experiences: [
      {
        id: 'limits', title: '按题型整理极限的解法',
        summary: '把常见的变形步骤和使用条件记在一起。',
        tips: ['遇到未定式先识别其类型，再选择等价无穷小、因式分解或洛必达法则等适用方法。'],
      },
    ],
    exams: [],
  },
  {
    id: 'linear-algebra', name: '线性代数', aliases: ['线代', '线性代数A', '线性代数B'],
    summary: '学习矩阵、线性方程组、向量空间、特征值与特征向量。',
    prerequisites: '高中数学',
    topics: ['行列式与矩阵', '线性方程组', '向量组的线性相关性', '特征值与特征向量'],
    teachers: [],
    experiences: [
      {
        id: 'matrix-operations', title: '把矩阵运算和几何意义放在一起学',
        summary: '通过小规模矩阵理解消元、线性变换与特征向量。',
        tips: ['手算几组二阶矩阵，画出它们对平面向量的作用，再把结论对应到公式上。'],
      },
    ],
    exams: [],
  },
].map((course) => ({ ...course, source: 'demo' }));

function normalizeSearch(text) {
  return text.normalize('NFKC').toLowerCase().replace(/[\s·,，、（）()_-]+/g, '');
}

export function findCourses(query) {
  const search = normalizeSearch(query);
  if (!search) return [];

  const exact = [];
  const partial = [];
  for (const course of courses) {
    const names = [course.name, ...course.aliases].map(normalizeSearch);
    if (names.includes(search)) exact.push(course);
    else if (names.some((name) => name.includes(search))) partial.push(course);
  }
  return [...exact, ...partial];
}

export function examTitle(exam) {
  return `${exam.year} 学年${exam.term} · ${exam.type}真题`;
}

export function answerLabel(exam) {
  if (exam.answers === true) return '附参考答案';
  if (exam.answers === false) return '暂无参考答案';
  return '参考答案待核实';
}

const accessLabels = {
  public: '公开访问',
  campus_login: '需校园账号',
  campus_network: '需校园网',
  vpn: '需校园 VPN',
  restricted: '需授权访问',
};

export function accessLabel(access) {
  return Object.hasOwn(accessLabels, access) ? accessLabels[access] : '';
}

export function resourceHref(value) {
  if (typeof value !== 'string' || /[\\\u0000-\u001f\u007f]/.test(value)) return null;
  if (value.startsWith('/') && !value.startsWith('//')) return value;
  try {
    const url = new URL(value);
    return ['https:', 'http:'].includes(url.protocol) && !url.username && !url.password ? url.href : null;
  } catch {
    return null;
  }
}
