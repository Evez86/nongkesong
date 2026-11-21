export const MAP_WIDTH = 1480;
export const MAP_HEIGHT = 934;
export const INITIAL_STAGE = 'term-5';

// Positions use the same coordinate space as the dotted route and map artwork.
export const stages = [
  {
    id: 'term-1', term: '大一上', shortTitle: '建立学习习惯',
    x: 199, y: 683, size: 90, angle: -7, sticker: [111, 101, 350, 394],
    title: '找到自己的学习节奏',
    description: '熟悉课程安排，慢慢找到适合自己的复习方式。',
    actions: ['把上课和自习时间记进课表', '每周整理一次课堂笔记', '试一种课后复习方法'],
  },
  {
    id: 'term-2', term: '大一下', shortTitle: '认识自己的专业',
    x: 385, y: 616, size: 92, angle: 5, sticker: [1040, 99, 409, 393],
    title: '了解专业有哪些方向',
    description: '先认识专业课程和真实应用，再记录自己想进一步了解的方向。',
    actions: ['浏览专业培养方案', '挑选两个方向各读一份入门资料', '写下想继续了解的问题'],
  },
  {
    id: 'term-3', term: '大二上', shortTitle: '打好专业基础',
    x: 311, y: 393, size: 116, angle: -5, sticker: [24, 287, 480, 502], destination: true, labelAbove: true,
    title: '补齐一门核心课的基础',
    description: '选一门对后续课程重要的课，把容易混淆的知识点整理成自己的笔记。',
    actions: ['列出最薄弱的三个知识点', '为每个知识点做一道练习', '期末前整理成一页复习清单'],
  },
  {
    id: 'term-4', term: '大二下', shortTitle: '尝试一次实践',
    x: 523, y: 474, size: 116, angle: -4, sticker: [487, 637, 514, 284],
    title: '参加一次小型实践',
    description: '找一项时间上可安排的实践，用课堂学到的方法解决一个小问题。',
    actions: ['找一项符合时间安排的实践', '给自己定一个具体的分工', '结束后记下收获和待改进的问题'],
  },
  {
    id: 'term-5', term: '大三上', shortTitle: '做一个小项目',
    x: 665, y: 326, size: 105, angle: 7, sticker: [101, 524, 340, 434], labelAbove: true,
    title: '把兴趣做成一个小项目',
    description: '选一个感兴趣的问题，做出一件能展示过程和结果的小作品。',
    actions: ['定一个学期内能完成的题目', '每周记下尝试和结果', '整理成一页作品说明'],
  },
  {
    id: 'term-6', term: '大三下', shortTitle: '整理项目作品',
    x: 868, y: 467, size: 113, angle: 4, sticker: [1027, 520, 450, 437],
    title: '整理自己做过的作品',
    description: '把课内和课外的项目归档，挑出最能说明自己做过什么的作品。',
    actions: ['挑选两项想保留的作品', '补齐过程、结果和个人分工', '请一位同学帮忙看说明'],
  },
  {
    id: 'term-7', term: '大四上', shortTitle: '筹备毕业去向',
    x: 992, y: 303, size: 130, angle: -5, sticker: [503, 225, 535, 577], destination: true, labelAbove: true,
    title: '确定毕业前的行动计划',
    description: '根据想去的方向列出重要日期，给毕业相关任务留出时间。',
    actions: ['核对自己的毕业要求', '整理近期要准备的材料', '把关键日期记进计划'],
  },
  {
    id: 'term-8', term: '大四下', shortTitle: '回顾四年成长',
    x: 1220, y: 248, size: 124, angle: 6, sticker: [1081, 336, 430, 452], destination: true,
    title: '整理四年的收获',
    description: '回顾大学期间的学习、作品和实践经历，留下以后想回看的记录。',
    actions: ['整理值得保留的课程与作品', '写下一件让自己自豪的事', '定下毕业后的第一个小目标'],
  },
];
