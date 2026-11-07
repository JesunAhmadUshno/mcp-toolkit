// Known-answer check, run by "npm run build" before vite. Fails the build unless
// the JavaScript port in guard.js reproduces the Python source and results:
//  1. constants match level-3-deep/mcp_deep.py,
//  2. the 30 Deep plan inputs (deep_plan.json) give the recorded status, reason,
//     code, result and audit log of results_deep.json, and the same summary,
//  3. every guard corpus case gives the Python verdict in results_guard.json,
//  4. the level README grades parse and their deductions sum to 10,000 minus the grade.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import * as G from './guard.js';
import { parseGrade, parseBullets, parseRoadmap, measuredDate } from './docs.js';

const root = new URL('../../', import.meta.url);
const read = (p) => fs.readFileSync(new URL(p, root), 'utf8');
const json = (p) => JSON.parse(read(p));

// 1. constants parity with the Python source
const py = read('level-3-deep/mcp_deep.py');
const tuple = (name) => [...py.match(new RegExp(`^${name} = \\(([^)]*)\\)`, 'm'))[1].matchAll(/"(\w+)"/g)].map((m) => m[1]);
const set = (name) => [...py.match(new RegExp(`^${name} = \\{([^}]*)\\}`, 'm'))[1].matchAll(/"(\w+)"/g)].map((m) => m[1]).sort();
assert.equal(G.MAX_BODY_BYTES, +py.match(/^MAX_BODY_BYTES = (\d+)/m)[1]);
assert.equal(G.PROTOCOL_VERSION, py.match(/^PROTOCOL_VERSION = "([^"]+)"/m)[1]);
assert.deepEqual(G.READ_TOOLS, tuple('READ_TOOLS'));
assert.deepEqual(G.CALC_TOOLS, tuple('CALC_TOOLS'));
assert.deepEqual(G.WRITE_TOOLS, tuple('WRITE_TOOLS'));
assert.deepEqual(G.DELETE_TOOLS, tuple('DELETE_TOOLS'));
assert.deepEqual([...G.SAFETY_REASONS].sort(), set('SAFETY_REASONS'));
assert.deepEqual([...G.BLOCKED_SQL_WORDS].sort(), set('BLOCKED_SQL_WORDS'));
for (const [k, v] of Object.entries(G.ERR)) assert.equal(v, +py.match(new RegExp(`^ERR_${k} = (-\\d+)`, 'm'))[1], `ERR_${k}`);
const fixtures = Object.fromEntries([...py.match(/^FIXTURE_FILES = \{([^}]*)\}/m)[1].matchAll(/"([^"]+)": "([^"]*)"/g)].map((m) => [m[1], m[2].replace(/\\n/g, '\n')]));
assert.deepEqual(G.FIXTURE_FILES, fixtures);
const seed = [...py.match(/^SEED_ROWS = \[([\s\S]*?)\]/m)[1].matchAll(/"id": (\d+), "name": "(\w+)", "score": (\d+)/g)].map((m) => ({ id: +m[1], name: m[2], score: +m[3] }));
assert.deepEqual(G.SEED_ROWS, seed);

// 2. the recorded Deep run, replayed call by call
const deep = json('level-3-deep/results_deep.json');
const plan = json('level-3-deep/deep_plan.json');
const recordedQueries = new Map([[plan[5].arguments.sql, deep.calls[5].result.rows]]);
assert.equal(plan.length, deep.summary.total_calls);
const audit = [];
const replay = plan.map((p, i) => {
  const r = G.evaluate({ token: p.token, id: p.request_id, method: p.method, tool: p.tool, args: G.planArgs(p) }, recordedQueries);
  const c = deep.calls[i];
  assert.equal(r.http, c.http_status, `${p.call} http`);
  assert.equal(r.category, c.status, `${p.call} status`);
  assert.equal(r.reason, c.error_reason ?? null, `${p.call} reason`);
  if (c.error_code !== undefined) assert.equal(r.code, c.error_code, `${p.call} code`);
  if (c.status === 'success') assert.deepEqual(r.response.result, c.result, `${p.call} result`);
  if (r.audit) audit.push({ seq: audit.length + 1, ...r.audit });
  return r;
});
assert.deepEqual(audit, deep.audit_log);
const count = (k) => replay.filter((r) => r.category === k).length;
const byReason = {};
for (const r of replay) if (r.category === 'safety_blocked') byReason[r.reason] = (byReason[r.reason] || 0) + 1;
assert.deepEqual(
  { successes: count('success'), unauthenticated: count('unauthenticated'), role_blocked: count('role_blocked'), safety_blocked: count('safety_blocked'), errors: count('error'), safety_by_reason: byReason, audit_entries: audit.length, reader_tools: G.ROLE_TOOLS.reader.length, operator_tools: G.ROLE_TOOLS.operator.length, total_tools: G.ALL_TOOLS.length },
  { successes: deep.summary.successes, unauthenticated: deep.summary.unauthenticated, role_blocked: deep.summary.role_blocked, safety_blocked: deep.summary.safety_blocked, errors: deep.summary.errors, safety_by_reason: deep.summary.safety_by_reason, audit_entries: deep.summary.audit_entries, reader_tools: deep.summary.reader_tools, operator_tools: deep.summary.operator_tools, total_tools: deep.summary.total_tools });

// 3. the labelled guard corpus, against the Python verdicts
const guard = json('level-3-deep/results_guard.json');
assert.equal(guard.summary.deep_replay_matches_results_deep, true);
for (const c of guard.sql) assert.equal(G.checkSql(c.sql) ?? 'allowed', c.verdict, `${c.id} ${c.sql}`);
for (const c of guard.path) {
  const v = G.readFileVerdict(c.path.replace(guard.sandbox_placeholder, G.SANDBOX_ROOT));
  assert.equal(v.reason ?? 'allowed', c.verdict, `${c.id} ${c.path}`);
}

// 4. docs parsed by the page
const grades = ['level-1-learn', 'level-2-build', 'level-3-deep'].map((l) => parseGrade(read(`${l}/README.md`)));
for (const g of grades) assert.equal(g.grade, g.max - g.items.reduce((s, i) => s + i.points, 0));
assert.ok(parseBullets(read('level-3-deep/README.md'), 'Failure modes and limits').length > 0);
assert.ok(parseRoadmap(read('ROADMAP.md')).length > 0);
measuredDate(read('level-3-deep/README.md'));

console.log('guard ok', { deepCalls: replay.length, auditEntries: audit.length, sqlCases: guard.sql.length, pathCases: guard.path.length, grades: grades.map((g) => g.grade) });
