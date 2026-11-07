// Parsers for the repo's own Markdown, run at build time (Vite ?raw imports in
// the page, fs reads in guard.check.mjs). Each throws on a shape it does not
// recognise, so a doc edit fails the build instead of showing stale numbers.

const num = (s) => +s.replace(/,/g, '');
const section = (md, heading) => {
  const parts = md.split(new RegExp(`^## ${heading}.*$`, 'm'));
  if (parts.length < 2) throw new Error(`missing "## ${heading}" section`);
  return parts[1].split(/^## /m)[0].trim();
};

// "## Grade": "8,700 of 10,000. Deductions, itemized and summing to 1,300: a, 400; b, 300; ... ."
export function parseGrade(md) {
  const para = section(md, 'Grade').split(/\n\s*\n/)[0].replace(/\s+/g, ' ');
  const m = para.match(/^([\d,]+) of ([\d,]+)\. Deductions, itemized and summing to ([\d,]+): (.*?)\.(?: [\d,]+ minus .*)?$/);
  if (!m) throw new Error(`grade paragraph not recognised: ${para.slice(0, 80)}`);
  const items = m[4].split(/;\s*/).map((it) => {
    const mm = it.match(/^(.*),\s*([\d,]+)$/);
    if (!mm) throw new Error(`deduction not recognised: ${it}`);
    return { text: mm[1], points: num(mm[2]) };
  });
  const grade = num(m[1]), max = num(m[2]), total = num(m[3]);
  const sum = items.reduce((s, i) => s + i.points, 0);
  if (sum !== total || grade !== max - sum) throw new Error(`deductions sum ${sum}, stated ${total}, grade ${grade} of ${max}`);
  return { grade, max, total, items };
}

export function parseBullets(md, heading) {
  const items = section(md, heading).split(/\n(?=- )/).filter((l) => l.startsWith('- ')).map((l) => l.slice(2).replace(/\s+/g, ' ').trim());
  if (!items.length) throw new Error(`no bullets under ${heading}`);
  return items;
}

export function parseRoadmap(md) {
  const items = [...section(md, 'v1.1 backlog').matchAll(/^(\d+)\. ([^:]+): (.+)$/gm)].map((m) => ({ n: +m[1], title: m[2], text: m[3] }));
  if (!items.length) throw new Error('no v1.1 backlog items');
  return items;
}

export function measuredDate(md) {
  const m = md.match(/## Results \(measured (\d{4}-\d{2}-\d{2})/);
  if (!m) throw new Error('no measured date');
  return m[1];
}
