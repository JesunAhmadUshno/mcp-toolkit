// Parsers for the repo's own Markdown, run at build time (Vite ?raw imports in
// the page, fs reads in guard.check.mjs). Each throws on a shape it does not
// recognise, so a doc edit fails the build instead of showing stale numbers.

const num = (s) => +s.replace(/,/g, '');
const section = (md, heading) => {
  const parts = md.split(new RegExp(`^## ${heading}.*$`, 'm'));
  if (parts.length < 2) throw new Error(`missing "## ${heading}" section`);
  return parts[1].split(/^## /m)[0].trim();
};

export function parseBullets(md, heading) {
  const items = section(md, heading).split(/\n(?=- )/).filter((l) => l.startsWith('- ')).map((l) => l.slice(2).replace(/\s+/g, ' ').trim());
  if (!items.length) throw new Error(`no bullets under ${heading}`);
  return items;
}

export function parseRoadmap(md) {
  const items = [...section(md, 'Future work').matchAll(/^(\d+)\. ([^:]+): (.+)$/gm)].map((m) => ({ n: +m[1], title: m[2], text: m[3] }));
  if (!items.length) throw new Error('no Future work items');
  return items;
}

export function measuredDate(md) {
  const m = md.match(/## Results \(measured (\d{4}-\d{2}-\d{2})/);
  if (!m) throw new Error('no measured date');
  return m[1];
}
