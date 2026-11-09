import { useMemo, useState, useEffect, useId } from 'react';
import learn from '../../level-1-learn/results_learn.json';
import build from '../../level-2-build/results_build.json';
import deep from '../../level-3-deep/results_deep.json';
import guardRes from '../../level-3-deep/results_guard.json';
import plan from '../../level-3-deep/deep_plan.json';
import learnMd from '../../level-1-learn/README.md?raw';
import buildMd from '../../level-2-build/README.md?raw';
import deepMd from '../../level-3-deep/README.md?raw';
import reportMd from '../../REPORT.md?raw';
import * as G from './guard.js';
import { parseBullets, parseRoadmap, measuredDate } from './docs.js';

const REPO = 'https://github.com/JesunAhmadUshno/mcp-toolkit';
const blob = (p) => `${REPO}/blob/main/${p}`;
const fmt = (n) => Number(n).toLocaleString('en-US');
const S = deep.summary;
const RUN_DATE = measuredDate(deepMd);
const recordedQueries = new Map([[plan[5].arguments.sql, deep.calls[5].result.rows]]);

const LEVELS = [
  { key: 'learn', name: 'Learn', prefix: 'C', data: learn, md: learnMd, file: 'level-1-learn', what: `in-process, ${Object.keys(learn.summary.tools_per_server).length} servers, ${learn.summary.total_tools} tools`, segs: [['successes', 'success'], ['blocked', 'blocked'], ['errors', 'error']] },
  { key: 'build', name: 'Build', prefix: 'B', data: build, md: buildMd, file: 'level-2-build', what: `${build.summary.transport} subprocesses, ${build.summary.servers.length} servers, ${build.summary.total_tools} tools`, segs: [['successes', 'success'], ['blocked', 'blocked'], ['errors', 'error']] },
  { key: 'deep', name: 'Deep', prefix: 'D', data: deep, md: deepMd, file: 'level-3-deep', what: `${S.transport.toUpperCase()} + bearer auth, ${S.roles.length} roles, ${S.total_tools} tools`, segs: [['successes', 'success'], ['unauthenticated', 'unauthenticated'], ['role_blocked', 'role_blocked'], ['safety_blocked', 'safety_blocked'], ['errors', 'error']] },
];
const STATUS_COLOR = { success: 'var(--good)', blocked: 'var(--bad)', safety_blocked: 'var(--bad)', unauthenticated: 'var(--warn)', role_blocked: 'var(--role)', error: 'var(--muted)' };
const STATUS_LABEL = { success: 'success', blocked: 'blocked', safety_blocked: 'safety block', unauthenticated: 'unauthenticated', role_blocked: 'role block', error: 'error' };
const PILL = { success: 'good', blocked: 'bad', safety_blocked: 'bad', unauthenticated: 'warn', role_blocked: 'role', error: 'muted' };
const CAT_COLOR = { auth: 'var(--warn)', authorization: 'var(--role)', safety: 'var(--bad)' };

const SECTIONS = [['top', 'Overview', '◎'], ['levels', 'Levels', '≡'], ['playground', 'Playground', '▶'], ['rules', 'Rules', '§'], ['roles', 'Roles', '⚿'], ['corpus', 'Corpus', '±'], ['trace', 'Trace', '⋯'], ['audit', 'Audit', '▤'], ['limits', 'Limits', '!']];

function useReveal() {
  useEffect(() => {
    const els = document.querySelectorAll('.reveal');
    if (!('IntersectionObserver' in window)) { els.forEach((e) => e.classList.add('in')); return; }
    const io = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } }), { threshold: 0.08 });
    els.forEach((e) => io.observe(e));
    return () => io.disconnect();
  }, []);
}

function MenuBar() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => { const t = setInterval(() => setNow(new Date()), 30000); return () => clearInterval(t); }, []);
  return (
    <div className="menubar" role="banner">
      <span className="apple" aria-hidden="true">◆</span>
      <a className="app" href="#top">mcp-toolkit</a>
      <a className="m" href={blob('PROPOSAL.md')}>Proposal</a>
      <a className="m" href={blob('level-3-deep/README.md')}>Deep level</a>
      <a className="m" href={blob('REPORT.md')}>Report</a>
      <span className="spacer" />
      <span className="status"><i /> Guard parity checked at build</span>
      <a href={REPO}>GitHub ↗</a>
      <span className="clock">{now.toLocaleString('en-US', { weekday: 'short', hour: 'numeric', minute: '2-digit' })}</span>
    </div>
  );
}

function Dock() {
  const [active, setActive] = useState('top');
  useEffect(() => {
    const io = new IntersectionObserver((es) => es.forEach((e) => e.isIntersecting && setActive(e.target.id)), { rootMargin: '-45% 0px -50% 0px' });
    SECTIONS.forEach(([id]) => { const el = document.getElementById(id); if (el) io.observe(el); });
    return () => io.disconnect();
  }, []);
  return (
    <nav className="dock" aria-label="Sections">
      {SECTIONS.map(([id, label, icon]) => (
        <a key={id} href={`#${id}`} className={active === id ? 'on' : ''} aria-current={active === id ? 'true' : undefined}>
          <span className="ico" aria-hidden="true">{icon}</span><span className="lbl">{label}</span>
        </a>
      ))}
    </nav>
  );
}

function Range({ label, value, min, max, step, onChange, show }) {
  const id = useId();
  return (
    <div className="field">
      <label htmlFor={id}>{label} <span>{show}</span></label>
      <input id={id} type="range" min={min} max={max} step={step} value={value} onChange={(e) => onChange(+e.target.value)} />
    </div>
  );
}

// A playground preset from a Deep plan entry, a SQL string or a path.
const fromPlan = (p) => ({ token: p.token, method: p.method, tool: p.tool ?? '', argsText: p.method === 'tools/call' ? JSON.stringify(G.planArgs(p) ?? null, null, 1) : '{}', label: p.call });
const sqlPreset = (sql, label) => ({ token: 'reader', method: 'tools/call', tool: 'run_query', argsText: JSON.stringify({ sql }, null, 1), label });
const pathPreset = (path, label) => ({ token: 'reader', method: 'tools/call', tool: 'read_file', argsText: JSON.stringify({ path }, null, 1), label });

export default function App() {
  useReveal();
  const [preset, setPreset] = useState(() => fromPlan(plan[14]));
  const load = (p) => { setPreset({ ...p, nonce: Math.random() }); document.getElementById('playground')?.scrollIntoView({ behavior: 'smooth' }); };
  return (
    <div className="wrap">
      <MenuBar />
      <div className="glow" aria-hidden="true" />
      <Hero />
      <Levels />
      <Playground preset={preset} />
      <Rules load={load} />
      <Roles />
      <Corpus load={load} />
      <Trace />
      <Audit />
      <Limits />
      <Roadmap />
      <Dock />
      <footer>
        Code: Apache-2.0. Every number on this page is read at build time from <code>level-*/results_*.json</code>, <code>level-3-deep/results_guard.json</code> and the level READMEs.
        Traces and the audit log are recorded runs from {RUN_DATE}; the playground is a JavaScript port of the Deep guard that runs in your browser and is checked against those runs on every build.
      </footer>
    </div>
  );
}

function Hero() {
  const tiles = [
    [S.total_calls, 'HTTP calls in the recorded Deep run'],
    [S.successes, 'legitimate calls served'],
    [S.unauthenticated, 'callers without a valid token (HTTP 401)'],
    [S.role_blocked, 'calls outside the caller’s role (HTTP 403)'],
    [S.safety_blocked, `safety blocks across ${Object.keys(S.safety_by_reason).length} named rules`],
    [S.errors, 'ordinary named errors (not blocks)'],
    [S.audit_entries, 'audit log entries written'],
    [`${S.reader_tools} / ${S.operator_tools}`, 'tools visible to reader / operator'],
  ];
  return (
    <header className="card hero window" id="top" data-title="mcp-toolkit.app">
      <div className="head">
        <p className="eyebrow">MCP-style tool server · three levels · recorded {RUN_DATE}</p>
        <span className="pill good">● {fmt(S.safety_blocked + S.role_blocked + S.unauthenticated)} stopped before a tool ran</span>
      </div>
      <h1>Tools with <em>rules</em>: {S.successes} of {S.total_calls} calls got through, and every refusal had a name.</h1>
      <p className="sub">
        Across {S.total_calls} HTTP calls to the authenticated Deep server, the toolkit served {S.successes} legitimate calls.
        It stopped {S.unauthenticated} callers without a valid token, {S.role_blocked} calls outside the caller’s role and {S.safety_blocked} unsafe requests, all before any tool ran, and wrote an audit entry for each.
      </p>
      <p className="hint scope">
        Honest scope: an MCP-style protocol in stdlib Python, not the official MCP SDK; localhost only, no TLS, two fixed bearer-token roles, tiny synthetic fixtures. No interop with real MCP clients has been measured.
      </p>
      <div className="actions">
        <a className="btn primary" href="#playground">Try the safety rule playground</a>
        <a className="btn ghost" href={blob('level-3-deep/README.md')}>Read the Deep level</a>
        <span className="hint">Reproduce with <code>python level-3-deep/run_deep.py</code></span>
      </div>
      <div className="tiles">
        {tiles.map(([n, cap]) => <div className="tile" key={cap}><div className="num">{n}</div><div className="cap">{cap}</div></div>)}
      </div>
    </header>
  );
}

function Levels() {
  const [hover, setHover] = useState(null);
  return (
    <section id="levels" className="card window reveal" data-title="levels.md">
      <p className="eyebrow">Three levels, one protocol</p>
      <h2>The same JSON-RPC shapes, carried <em>further</em> each time.</h2>
      <p className="sub">Each bar is one recorded run: every call the runner made, stacked by outcome. Learn passes dicts in process, Build talks to real subprocesses over stdio, Deep serves HTTP with bearer tokens and roles. Hover a segment for its count.</p>
      <div className="levels">
        {LEVELS.map((L) => {
          const s = L.data.summary;
          const total = s.total_calls;
          let x = 0;
          return (
            <div className="level" key={L.key}>
              <div className="lab"><b>{L.name}</b><span className="hint">{L.what}</span><span className="mono">{total} calls</span></div>
              <svg className="chart" viewBox="0 0 600 22" preserveAspectRatio="none" role="img" aria-label={`${L.name} outcomes: ${L.segs.map(([k, st]) => `${s[k]} ${STATUS_LABEL[st]}`).join(', ')}`} onMouseLeave={() => setHover(null)}>
                {L.segs.map(([k, st]) => {
                  const w = (s[k] / total) * 600; const r = <rect key={k} x={x} y={0} width={Math.max(0, w - 2)} height={22} rx={4} fill={STATUS_COLOR[st]} opacity={hover && hover.level !== L.key ? 0.35 : hover && hover.st !== st ? 0.5 : 0.9} onMouseEnter={() => setHover({ level: L.key, st, n: s[k], total, name: L.name })} />;
                  x += w; return r;
                })}
              </svg>
            </div>
          );
        })}
      </div>
      <div className="legend">{['success', 'blocked', 'unauthenticated', 'role_blocked', 'safety_blocked', 'error'].map((k) => <span key={k}><i style={{ background: STATUS_COLOR[k] }} />{STATUS_LABEL[k]}</span>)}</div>
      <div className="tip" aria-live="polite">{hover ? `${hover.name}: ${hover.n} of ${hover.total} calls were ${STATUS_LABEL[hover.st]}.` : 'Learn and Build count blocks as one group; Deep splits refusals into authentication, role and safety.'}</div>
    </section>
  );
}

const STEPS = ['Size cap', 'Bearer token', 'Method', 'Intent', 'Role allowlist', 'Arguments', 'Path / SQL rules', 'Tool ran'];
const STAGE_INDEX = { 'size cap': 0, authentication: 1, dispatch: 2, intent: 3, 'role allowlist': 4, arguments: 5, 'path rules': 6, 'SQL guard': 6, 'tool ran': 7 };
const TOKENS = [['reader', 'reader token'], ['operator', 'operator token'], ['none', 'no token'], ['wrong', 'wrong token']];
const METHODS = ['tools/call', 'initialize', 'tools/list', 'bogus/method'];

function Playground({ preset }) {
  const [token, setToken] = useState(preset.token);
  const [method, setMethod] = useState(preset.method);
  const [tool, setTool] = useState(preset.tool);
  const [argsText, setArgsText] = useState(preset.argsText);
  const [from, setFrom] = useState(preset.label);
  useEffect(() => { setToken(preset.token); setMethod(preset.method); setTool(preset.tool); setArgsText(preset.argsText); setFrom(preset.label); }, [preset]);
  const parsed = useMemo(() => { if (method !== 'tools/call') return { ok: true, v: undefined }; try { return { ok: true, v: JSON.parse(argsText) }; } catch (e) { return { ok: false, msg: e.message }; } }, [argsText, method]);
  const recorded = plan.find((p) => p.call === from);
  const r = useMemo(() => parsed.ok ? G.evaluate({ token, id: recorded?.request_id ?? 1, method, tool, args: parsed.v }, recordedQueries) : null, [parsed, token, method, tool, recorded]);
  const stop = r ? STAGE_INDEX[r.stage] : -1;
  const tone = r ? (r.category === 'success' ? 'good' : r.category === 'error' ? 'warn' : 'bad') : 'muted';
  const probes = ['S05', 'S06', 'S19', 'S03'].map((id) => guardRes.sql.find((c) => c.id === id));
  const ids = { token: useId(), method: useId(), tool: useId(), args: useId(), rec: useId(), list: useId() };
  const edit = (f) => (e) => { f(e.target.value); setFrom(null); };
  const [pad, setPad] = useState(0);
  const padTo = (n) => { setPad(n); setToken('operator'); setMethod('tools/call'); setTool('count_words'); setArgsText(JSON.stringify({ text: 'x '.repeat(n) })); setFrom(null); };
  return (
    <section id="playground" className="card window reveal" data-title="guard.playground — live">
      <div className="head">
        <div>
          <p className="eyebrow">Live in your browser</p>
          <h2>Send a request and watch which rule <em>stops</em> it.</h2>
          <p className="sub">
            A JavaScript port of the Deep server’s request pipeline in <a href={blob('level-3-deep/mcp_deep.py')}>mcp_deep.py</a>: size cap, bearer token, intent classification, role allowlist, then the per-tool path and SQL rules.
            The build replays all {plan.length} recorded Deep calls and {guardRes.sql.length + guardRes.path.length} corpus cases through it and fails on any mismatch with the Python results.
          </p>
        </div>
        <span className="pill info">computed live</span>
      </div>
      <div className="controls">
        <div className="field"><label htmlFor={ids.rec}>Load a recorded call</label>
          <select id={ids.rec} value={from && recorded ? from : ''} onChange={(e) => { const p = plan.find((x) => x.call === e.target.value); if (p) { const f = fromPlan(p); setToken(f.token); setMethod(f.method); setTool(f.tool); setArgsText(f.argsText); setFrom(p.call); } }}>
            <option value="">(custom request)</option>
            {plan.map((p, i) => <option key={p.call} value={p.call}>{p.call} · {p.token} · {p.tool ?? p.method} → {deep.calls[i].error_reason ?? deep.calls[i].status}</option>)}
          </select>
        </div>
        <div className="field"><label htmlFor={ids.token}>Bearer token</label>
          <select id={ids.token} value={token} onChange={edit(setToken)}>{TOKENS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select>
        </div>
        <div className="field"><label htmlFor={ids.method}>Method</label>
          <select id={ids.method} value={method} onChange={edit(setMethod)}>{METHODS.map((m) => <option key={m}>{m}</option>)}</select>
        </div>
        <div className="field"><label htmlFor={ids.tool}>Tool name (free text)</label>
          <input id={ids.tool} className="text" list={ids.list} value={tool} disabled={method !== 'tools/call'} onChange={edit(setTool)} spellCheck="false" autoComplete="off" />
          <datalist id={ids.list}>{[...G.ALL_TOOLS, ...G.WRITE_TOOLS, ...G.DELETE_TOOLS].map((t) => <option key={t} value={t} />)}</datalist>
        </div>
      </div>
      <div className="field"><label htmlFor={ids.args}>Arguments (JSON) <span>{r ? `${fmt(r.bodyBytes)} of ${fmt(G.MAX_BODY_BYTES)} bytes` : ''}</span></label>
        <textarea id={ids.args} className="args" rows={3} value={argsText} disabled={method !== 'tools/call'} onChange={edit(setArgsText)} spellCheck="false" />
      </div>
      <div className="controls one">
        <Range label="Size probe: count_words text of “x ” repeated" value={pad} min={0} max={6000} step={50} onChange={padTo} show={`${fmt(pad)} times`} />
      </div>
      <div className="probes" role="group" aria-label="SQL guard probes">
        <span className="hint">SQL guard probes:</span>
        {probes.map((c) => <button key={c.id} className="chip" onClick={() => { const p = sqlPreset(c.sql); setToken(p.token); setMethod(p.method); setTool(p.tool); setArgsText(p.argsText); setFrom(null); }} title={c.note}><span className="mono">{c.sql}</span></button>)}
      </div>
      {!parsed.ok && <p className="pill warn">Arguments are not valid JSON: {parsed.msg}</p>}
      {r && (
        <>
          <ol className="pipe" aria-label="Pipeline stages">
            {STEPS.map((s, i) => <li key={s} className={i < stop ? 'pass' : i === stop ? `stop ${tone}` : 'skip'}>{s}</li>)}
          </ol>
          <div className="tiles verdict">
            <div className="tile"><div className="num">{r.http}</div><div className="cap">HTTP status</div></div>
            <div className="tile"><div className="num">{r.code ?? '—'}</div><div className="cap">JSON-RPC error code</div></div>
            <div className="tile"><div className={`num word ${tone}`}>{r.reason ?? 'ok'}</div><div className="cap">reason</div></div>
            <div className="tile"><div className={`num word ${tone}`}>{STATUS_LABEL[r.category]}</div><div className="cap">outcome, stopped at “{STEPS[stop]}”</div></div>
          </div>
          {r.executed === false && <p className="hint note">{r.recordedRows ? `Passes the guard. Rows shown are the recorded result of call D06 (${RUN_DATE}), not computed here.` : 'Passes the guard; would execute on sqlite. Allowed queries are not run in the browser, so no rows are shown.'}</p>}
          {method === 'tools/call' && tool === 'read_file' && <p className="hint note">Virtual sandbox at <code>{G.SANDBOX_ROOT}</code> holding {Object.keys(G.FIXTURE_FILES).join(', ')}. No real filesystem and no symlinks, so symlink behaviour of the Python server cannot be shown here.</p>}
          {recorded && <p className="hint note">Matches recorded call {recorded.call}: HTTP {deep.calls[plan.indexOf(recorded)].http_status}, {deep.calls[plan.indexOf(recorded)].error_reason ?? deep.calls[plan.indexOf(recorded)].status}.</p>}
          <div className="grid2 out">
            <div><h3>Response</h3><pre className="code">{JSON.stringify(r.response, null, 2)}</pre></div>
            <div><h3>Audit entry it would write</h3><pre className="code">{r.audit ? JSON.stringify(r.audit, null, 2) : 'none: ordinary results and named errors are not audited'}</pre></div>
          </div>
        </>
      )}
    </section>
  );
}

const RULE_TEXT = {
  path_traversal: 'A path with a .. segment (split on / or \\), or a relative path that resolves outside the sandbox.',
  absolute_path_blocked: 'An absolute path that resolves outside the sandbox.',
  write_blocked: `A call to ${G.WRITE_TOOLS.join(', ')}. No write tool exists; the attempt itself is the block.`,
  delete_blocked: `A call to ${G.DELETE_TOOLS.join(', ')}. Same pattern as writes.`,
  sql_not_select: `SQL whose first word is not SELECT, or with any of ${G.BLOCKED_SQL_WORDS.length} blocked words (INSERT, DROP, PRAGMA …) anywhere.`,
  sql_multi_statement: 'A semicolon left after trailing semicolons are stripped. Checked before the SELECT rule.',
  request_too_large: `A body over ${fmt(G.MAX_BODY_BYTES)} bytes by declared Content-Length: HTTP 413 before parsing or auth.`,
  unknown_tool: `Any other tool name outside the ${G.ALL_TOOLS.length}-tool registry.`,
};

function Rules({ load }) {
  const corpusHits = (r) => [...guardRes.sql, ...guardRes.path].filter((c) => c.verdict === r).length;
  return (
    <section id="rules" className="card window reveal" data-title="safety_rules.json">
      <p className="eyebrow">Rule catalogue</p>
      <h2>{G.SAFETY_REASONS.length} named safety rules, each with an <em>audit</em> entry.</h2>
      <p className="sub">Enforced on the server before any tool runs. Recorded counts come from the Deep run’s <code>safety_by_reason</code>; corpus counts from <a href={blob('level-3-deep/results_guard.json')}>results_guard.json</a>. “Try it” loads the recorded call that tripped the rule into the playground.</p>
      <div className="rules">
        {G.SAFETY_REASONS.map((r) => {
          const i = deep.calls.findIndex((c) => c.error_reason === r);
          return (
            <div className="tile rule" key={r}>
              <div className="head" style={{ marginBottom: 6 }}><span className="mono rname">{r}</span><span className="pill bad">{S.safety_by_reason[r] ?? 0} recorded</span></div>
              <p className="hint" style={{ margin: 0 }}>{RULE_TEXT[r]}</p>
              <div className="rfoot"><span className="hint">{corpusHits(r) ? `${corpusHits(r)} corpus case${corpusHits(r) === 1 ? '' : 's'}` : 'not in the SQL and path corpus'}</span>{i >= 0 && <button className="btn ghost sm" onClick={() => load(fromPlan(plan[i]))}>Try it ({plan[i].call})</button>}</div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function Roles() {
  const rows = [...G.ALL_TOOLS.map((t) => ({ t, kind: G.READ_TOOLS.includes(t) ? 'read' : 'calc' })), ...G.WRITE_TOOLS.map((t) => ({ t, kind: 'write' })), ...G.DELETE_TOOLS.map((t) => ({ t, kind: 'delete' }))];
  const roles = Object.keys(G.ROLE_TOOLS);
  return (
    <section id="roles" className="card window reveal" data-title="roles.cfg">
      <p className="eyebrow">Role matrix</p>
      <h2>Two roles, {G.ALL_TOOLS.length} tools, and no way to <em>write</em>.</h2>
      <p className="sub">Built from <code>ROLE_TOOLS</code>. The allowlist is enforced on the server, and <code>tools/list</code> is filtered per role ({S.reader_tools} for reader, {S.operator_tools} for operator). Write and delete names are never offered to anyone: calling one is a safety block, recorded under its own reason, even before the role check.</p>
      <div className="scroll-x">
        <table className="matrix">
          <thead><tr><th>Tool</th><th>Kind</th>{roles.map((r) => <th key={r}>{r}</th>)}</tr></thead>
          <tbody>
            {rows.map(({ t, kind }) => (
              <tr key={t}><td className="mono">{t}</td><td>{kind}</td>
                {roles.map((r) => kind === 'write' || kind === 'delete'
                  ? <td key={r} className="no">never offered</td>
                  : G.ROLE_TOOLS[r].includes(t) ? <td key={r} className="ok">✓ allowed</td> : <td key={r} className="muted">403 forbidden_role</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function Corpus({ load }) {
  const [show, setShow] = useState('wrong');
  const all = [...guardRes.sql.map((c) => ({ ...c, kind: 'sql', input: c.sql })), ...guardRes.path.map((c) => ({ ...c, kind: 'path', input: c.path }))];
  const rows = all.filter((c) => show === 'all' || (show === 'wrong' ? c.outcome.startsWith('false') : c.outcome.startsWith('true')));
  const sum = guardRes.summary;
  const OUT = { false_positive: ['warn', 'false positive'], false_negative: ['bad', 'false negative'], true_positive: ['good', 'blocked, correct'], true_negative: ['good', 'allowed, correct'] };
  return (
    <section id="corpus" className="card window reveal" data-title={`results_guard.json — ${all.length} labelled cases`}>
      <div className="head">
        <div>
          <p className="eyebrow">Measured: where a token guard falls short</p>
          <h2>The SQL guard blocks safe reads and <em>misses</em> schema reads.</h2>
          <p className="sub">
            <a href={blob('level-3-deep/guard_corpus.py')}>guard_corpus.py</a> runs the Python guards over hand-labelled inputs. Labels follow the tool contracts: one read-only SELECT on the items table, one file inside the sandbox.
            It is a small corpus, so these are counts on these cases, not error rates for real traffic.
          </p>
        </div>
        <div className="seg" role="group" aria-label="Filter corpus cases">
          {[['wrong', 'Mistakes'], ['right', 'Correct'], ['all', 'All']].map(([k, l]) => <button key={k} aria-pressed={show === k} onClick={() => setShow(k)}>{l}</button>)}
        </div>
      </div>
      <div className="tiles">
        <div className="tile"><div className="num">{sum.sql.false_positive}<small> / {sum.sql.true_negative + sum.sql.false_positive}</small></div><div className="cap">safe SQL reads wrongly blocked</div></div>
        <div className="tile"><div className="num">{sum.sql.false_negative}<small> / {sum.sql.true_positive + sum.sql.false_negative}</small></div><div className="cap">unwanted SQL let through</div></div>
        <div className="tile"><div className="num">{sum.path.false_positive}<small> / {sum.path.true_negative + sum.path.false_positive}</small></div><div className="cap">in-sandbox paths wrongly blocked</div></div>
        <div className="tile"><div className="num">{sum.path.false_negative}<small> / {sum.path.true_positive + sum.path.false_negative}</small></div><div className="cap">sandbox escapes let through</div></div>
      </div>
      <div className="scroll-x" style={{ marginTop: 16 }}>
        <table className="corpus">
          <thead><tr><th>Case</th><th>Input</th><th>Guard verdict</th><th>Outcome</th><th><span className="sr">Load</span></th></tr></thead>
          <tbody>
            {rows.map((c) => (
              <tr key={c.id}>
                <td className="mono">{c.id}</td>
                <td><span className="mono in">{c.input}</span><div className="hint">{c.note}</div></td>
                <td className="mono">{c.verdict}</td>
                <td><span className={`pill ${OUT[c.outcome][0]}`}>{OUT[c.outcome][1]}</span></td>
                <td><button className="btn ghost sm" onClick={() => load(c.kind === 'sql' ? sqlPreset(c.sql, null) : pathPreset(c.path.replace(guardRes.sandbox_placeholder, G.SANDBOX_ROOT), null))} aria-label={`Load ${c.id} in the playground`}>Try</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function Trace() {
  const [lv, setLv] = useState('deep');
  const [status, setStatus] = useState('all');
  const [reason, setReason] = useState('all');
  const [sel, setSel] = useState(14);
  const L = LEVELS.find((x) => x.key === lv);
  const calls = L.data.calls;
  const statuses = [...new Set(calls.map((c) => c.status))];
  const reasons = [...new Set(calls.map((c) => c.error_reason).filter(Boolean))];
  const shown = calls.filter((c) => (status === 'all' || c.status === status) && (reason === 'all' || c.error_reason === reason));
  const cur = calls.find((c) => c.seq === sel) ?? shown[0];
  const req = lv === 'deep' && cur ? plan[cur.seq - 1] : null;
  const ids = { st: useId(), rs: useId() };
  const id = (c) => `${L.prefix}${String(c.seq).padStart(2, '0')}`;
  const switchLevel = (k) => { setLv(k); setStatus('all'); setReason('all'); setSel(1); };
  return (
    <section id="trace" className="card window reveal" data-title="trace.ndjson — recorded">
      <div className="head">
        <div>
          <p className="eyebrow">Recorded replay · runs of {RUN_DATE}</p>
          <h2>Every recorded call, with the response it <em>actually</em> got.</h2>
          <p className="sub">Nothing here is re-run: this is the per-call JSON the three runners wrote to <code>results_learn.json</code>, <code>results_build.json</code> and <code>results_deep.json</code>. Deep calls also show the request side from <code>deep_plan.json</code> (bearer tokens shown as role labels only).</p>
        </div>
        <span className="pill warn">recorded, not live</span>
      </div>
      <div className="controls">
        <div className="field"><span className="flabel">Level</span>
          <div className="seg" role="group" aria-label="Level">{LEVELS.map((x) => <button key={x.key} aria-pressed={lv === x.key} onClick={() => switchLevel(x.key)}>{x.name} ({x.data.calls.length})</button>)}</div>
        </div>
        <div className="field"><label htmlFor={ids.st}>Status</label>
          <select id={ids.st} value={status} onChange={(e) => setStatus(e.target.value)}><option value="all">all statuses</option>{statuses.map((s) => <option key={s} value={s}>{STATUS_LABEL[s]}</option>)}</select>
        </div>
        <div className="field"><label htmlFor={ids.rs}>Reason</label>
          <select id={ids.rs} value={reason} onChange={(e) => setReason(e.target.value)}><option value="all">all reasons</option>{reasons.map((s) => <option key={s} value={s}>{s}</option>)}</select>
        </div>
      </div>
      <div className="trace">
        <ul className="calls" aria-label="Recorded calls">
          {shown.map((c) => (
            <li key={c.seq}><button className={cur && cur.seq === c.seq ? 'on' : ''} aria-pressed={cur && cur.seq === c.seq} onClick={() => setSel(c.seq)}>
              <span className="mono">{id(c)}</span><span className="cl">{c.role ? `${c.role} · ` : c.server ? `${c.server} · ` : ''}{c.label}</span><i style={{ background: STATUS_COLOR[c.status] }} title={STATUS_LABEL[c.status]} />
            </button></li>
          ))}
          {!shown.length && <li className="hint">No calls match these filters.</li>}
        </ul>
        <div className="detail">
          {cur ? <>
            <div className="head" style={{ marginBottom: 8 }}><h3>{id(cur)} · {cur.label}</h3><span className={`pill ${PILL[cur.status]}`}>{STATUS_LABEL[cur.status]}{cur.http_status ? ` · HTTP ${cur.http_status}` : ''}</span></div>
            {req && <><p className="hint">Request ({req.token === 'none' ? 'no token' : `${req.token} token`})</p><pre className="code">{JSON.stringify(G.makeRequest(req.request_id, req.method, req.tool ? { name: req.tool, arguments: req.oversize_repeat ? `"x " repeated ${fmt(req.oversize_repeat)} times` : req.arguments } : undefined), null, 2)}</pre></>}
            <p className="hint">Recorded entry</p>
            <pre className="code">{JSON.stringify(cur, null, 2)}</pre>
          </> : <p className="hint">Pick a call.</p>}
        </div>
      </div>
    </section>
  );
}

function Audit() {
  const [hover, setHover] = useState(null);
  const [cat, setCat] = useState('all');
  const log = deep.audit_log;
  const counts = log.reduce((m, e) => ({ ...m, [e.category]: (m[e.category] || 0) + 1 }), {});
  const W = log.length * 40;
  return (
    <section id="audit" className="card window reveal" data-title="audit.log — recorded">
      <div className="head">
        <div>
          <p className="eyebrow">Recorded audit log · Deep run of {RUN_DATE}</p>
          <h2>{log.length} refusals, {log.length} audit lines, <em>in order</em>.</h2>
          <p className="sub">Each block wrote one in-memory entry with its category, reason, tool and role, never a token or file content. Successful calls and ordinary errors write nothing. Hover a cell to read the entry.</p>
        </div>
        <div className="seg" role="group" aria-label="Filter audit category">
          {['all', ...Object.keys(counts)].map((k) => <button key={k} aria-pressed={cat === k} onClick={() => setCat(k)}>{k === 'all' ? `All ${log.length}` : `${k} ${counts[k]}`}</button>)}
        </div>
      </div>
      <svg className="chart" viewBox={`0 0 ${W} 44`} preserveAspectRatio="none" role="img" aria-label={`Audit log timeline: ${Object.entries(counts).map(([k, v]) => `${v} ${k}`).join(', ')}`} onMouseLeave={() => setHover(null)}>
        {log.map((e, i) => <rect key={e.seq} x={i * 40 + 2} y={hover?.seq === e.seq ? 0 : 4} width={36} height={hover?.seq === e.seq ? 44 : 36} rx={6} fill={CAT_COLOR[e.category]} opacity={cat === 'all' || cat === e.category ? 0.9 : 0.15} onMouseEnter={() => setHover(e)} onClick={() => setHover(e)} />)}
      </svg>
      <div className="legend">{Object.keys(counts).map((k) => <span key={k}><i style={{ background: CAT_COLOR[k] }} />{k} ({counts[k]})</span>)}</div>
      <div className="tip" aria-live="polite">{hover ? <>#{hover.seq} <b>{hover.category}</b> · <span className="mono">{hover.reason}</span> · tool {hover.tool ?? 'none'} · role {hover.role ?? 'none (no valid token)'}</> : 'Order follows the run: authentication first, then role, then the safety rules.'}</div>
    </section>
  );
}

function Limits() {
  const levels = LEVELS.map((L) => ({ L, items: parseBullets(L.md, 'Known limits') }));
  const fails = parseBullets(deepMd, 'Failure modes and limits');
  const [lv, setLv] = useState('deep');
  const cur = levels.find((x) => x.L.key === lv);
  return (
    <section id="limits" className="card window reveal" data-title="LIMITS.txt">
      <div className="head">
        <div>
          <p className="eyebrow">Written limits</p>
          <h2>What each level does <em>not</em> do, in the project’s own words.</h2>
          <p className="sub">Parsed at build time from the “Known limits” section of each level README, largest first; the build fails if a section goes missing. Self-assessed and not externally reviewed.</p>
        </div>
        <div className="seg" role="group" aria-label="Level limits">
          {levels.map(({ L, items }) => <button key={L.key} aria-pressed={lv === L.key} onClick={() => setLv(L.key)}>{L.name} ({items.length})</button>)}
        </div>
      </div>
      <div className="grid2">
        <div>
          <h3>Known limits ({cur.L.name})</h3>
          <ul className="fails">{cur.items.map((f) => <li key={f}>{f}</li>)}</ul>
        </div>
        <div>
          <h3>Written failure modes (Deep)</h3>
          <ul className="fails">{fails.map((f) => <li key={f}>{f}</li>)}</ul>
        </div>
      </div>
    </section>
  );
}

function Roadmap() {
  const items = parseRoadmap(reportMd);
  return (
    <section id="roadmap" className="card window reveal" data-title="REPORT.md">
      <p className="eyebrow">What’s next · v1.1 backlog</p>
      <h2>{items.length} things this project does <em>not</em> do yet.</h2>
      <p className="sub">Named at the v1.0 ship. None of it is claimed as done; an item leaves the list only with tests and measured results. See also the <a href={blob('REPORT.md')}>report</a> for what each gap would need.</p>
      <div className="docs roadmap">
        {items.map((it) => <div key={it.n} className="item"><span className="pill muted">not done</span><b>{it.n}. {it.title}</b><small>{it.text[0].toUpperCase() + it.text.slice(1)}</small></div>)}
      </div>
    </section>
  );
}

