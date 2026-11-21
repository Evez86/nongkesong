const categoryNames = {
  required: '必修',
  elective: '选修',
  practice: '实践',
  other: '其他',
};

function cleanText(value) {
  return typeof value === 'string' ? value.trim() : '';
}

function cleanNumber(value) {
  return Number.isFinite(value) && value >= 0 ? value : null;
}

function cleanPosition(value) {
  return Number.isInteger(value) && value >= 1 ? value : null;
}

export function readCampusPlan(data) {
  const id = cleanText(data?.plan_id);
  if (!id ||
    !['complete', 'partial'].includes(data.parse_status) || !Array.isArray(data.courses)) return null;

  const courses = data.courses.flatMap((course, index) => {
    const name = cleanText(course?.name);
    if (!name) return [];
    const term = cleanPosition(course.term);
    return [{
      id: cleanText(course.id) || String(index + 1),
      name,
      code: cleanText(course.code),
      term: term && term <= 8 ? term : null,
      category: cleanText(course.category),
      credits: cleanNumber(course.credits),
      source_ref: {
        page: cleanPosition(course.source_ref?.page),
        table: cleanPosition(course.source_ref?.table),
        row: cleanPosition(course.source_ref?.row),
      },
    }];
  });
  if (!courses.length) return null;

  const warnings = Array.isArray(data.warnings) ? data.warnings
    .map((warning) => cleanText(warning?.message)).filter(Boolean).map((message) => ({ message })) : [];
  const skippedCourse = courses.length !== data.courses.length;
  if (skippedCourse) {
    warnings.push({ message: '部分课程缺少名称，请对照学校记录核实。' });
  }

  return {
    plan_id: id,
    program_name: cleanText(data.program_name),
    cohort: Number.isInteger(data.cohort) ? String(data.cohort) : cleanText(data.cohort),
    parse_status: skippedCourse ? 'partial' : data.parse_status,
    courses,
    credit_summary: {
      parsed_credits: cleanNumber(data.credit_summary?.parsed_credits),
      graduation_target_credits: cleanNumber(data.credit_summary?.graduation_target_credits),
    },
    warnings,
  };
}

export function categoryLabel(category) {
  return Object.hasOwn(categoryNames, category) ? categoryNames[category] : category || '待核实';
}
