// JavaScript port of the Deep request pipeline in level-3-deep/mcp_deep.py
// (Handler.do_POST, ToolkitCore.dispatch, _call_tool, _read_file, _check_sql,
// _calculate, _count_words). guard.check.mjs runs at build time and fails the
// build unless these constants match the Python source and every verdict
// matches the recorded results_deep.json and results_guard.json.
//
// Differences by design: the sandbox is virtual (FIXTURE_FILES under
// SANDBOX_ROOT, no symlinks, no real filesystem), and an allowed run_query is
// never executed here; only the recorded D06 query shows its recorded rows.

export const PROTOCOL_VERSION = 'deep-1';
export const MAX_BODY_BYTES = 8192;
export const ERR = {
  INVALID_REQUEST: -32600, METHOD_NOT_FOUND: -32601, INVALID_PARAMS: -32602,
  UNAUTHENTICATED: -32010, FORBIDDEN_ROLE: -32011, TOOL_NOT_FOUND: -32001,
  SAFETY_BLOCKED: -32012, NOT_FOUND: -32004, QUERY: -32005, CALC: -32006, TOO_LARGE: -32013,
};
export const READ_TOOLS = ['read_file', 'list_files', 'list_items', 'run_query'];
export const CALC_TOOLS = ['calculate', 'count_words'];
export const ROLE_TOOLS = { reader: READ_TOOLS, operator: [...READ_TOOLS, ...CALC_TOOLS] };
export const ALL_TOOLS = [...READ_TOOLS, ...CALC_TOOLS];
export const WRITE_TOOLS = ['write_file', 'create_file', 'append_file'];
export const DELETE_TOOLS = ['delete_file', 'remove_file', 'unlink_file'];
export const SAFETY_REASONS = ['path_traversal', 'absolute_path_blocked', 'write_blocked', 'delete_blocked', 'sql_not_select', 'sql_multi_statement', 'request_too_large', 'unknown_tool'];
export const BLOCKED_SQL_WORDS = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'CREATE', 'REPLACE', 'TRUNCATE', 'GRANT', 'REVOKE', 'ATTACH', 'DETACH', 'VACUUM', 'PRAGMA'];
export const FIXTURE_FILES = { 'guide.txt': 'servers need hosts\n', 'hello.txt': 'hello mcp\n', 'notes.txt': 'tools need rules\n' };
export const SEED_ROWS = [{ id: 1, name: 'alpha', score: 10 }, { id: 2, name: 'beta', score: 20 }, { id: 3, name: 'gamma', score: 30 }];
export const SANDBOX_ROOT = '/sandbox';

const obj = (props, required) => ({ type: 'object', properties: props, required });
export const TOOL_DEFS = [
  { name: 'read_file', server: 'file', description: 'Read one text file inside the sandbox.', inputSchema: obj({ path: { type: 'string' } }, ['path']) },
  { name: 'list_files', server: 'file', description: 'List files inside the sandbox, sorted.', inputSchema: obj({}, []) },
  { name: 'list_items', server: 'database', description: 'List every row of the items table, by id.', inputSchema: obj({}, []) },
  { name: 'run_query', server: 'database', description: 'Run one read-only SELECT on the items table.', inputSchema: obj({ sql: { type: 'string' } }, ['sql']) },
  { name: 'calculate', server: 'calc', description: 'Safe arithmetic: add, subtract, multiply, divide.', inputSchema: obj({ op: { type: 'string' }, a: { type: 'number' }, b: { type: 'number' } }, ['op', 'a', 'b']) },
  { name: 'count_words', server: 'calc', description: 'Count whitespace separated words in a text.', inputSchema: obj({ text: { type: 'string' } }, ['text']) },
];

// Python json.dumps with default settings: ", " and ": " separators, ensure_ascii.
export function pyJson(v) {
  if (v === null || v === undefined) return 'null';
  if (typeof v === 'string') return JSON.stringify(v).replace(/[\u007f-￿]/g, (c) => '\\u' + c.charCodeAt(0).toString(16).padStart(4, '0'));
  if (typeof v !== 'object') return JSON.stringify(v);
  if (Array.isArray(v)) return '[' + v.map(pyJson).join(', ') + ']';
  return '{' + Object.entries(v).map(([k, x]) => pyJson(k) + ': ' + pyJson(x)).join(', ') + '}';
}

export const makeRequest = (id, method, params) => ({ jsonrpc: '2.0', id, method, params: params || {} });
const isObj = (x) => x !== null && typeof x === 'object' && !Array.isArray(x);
const err = (id, code, message, reason) => ({ jsonrpc: '2.0', id, error: { code, message, data: { reason } } });
const ok = (id, result) => ({ jsonrpc: '2.0', id, result });

export function checkSql(sql) {
  const core = sql.trim().replace(/;+$/, '');
  if (core.includes(';')) return 'sql_multi_statement';
  const words = sql.toUpperCase().match(/[A-Za-z]+/g) || [];
  if (!words.length || words[0] !== 'SELECT') return 'sql_not_select';
  if (words.slice(1).some((w) => BLOCKED_SQL_WORDS.includes(w))) return 'sql_not_select';
  return null;
}

// POSIX normpath for an absolute path (no symlinks in the virtual sandbox).
function normAbs(p) {
  const out = [];
  for (const seg of p.split('/')) {
    if (seg === '' || seg === '.') continue;
    if (seg === '..') out.pop(); else out.push(seg);
  }
  return '/' + out.join('/');
}
const inSandbox = (t) => t === SANDBOX_ROOT || t.startsWith(SANDBOX_ROOT + '/');

// Returns { reason, code, message } for a refusal or { content } for a read.
export function readFileVerdict(path) {
  if (typeof path !== 'string' || !path) return { reason: 'invalid_params', code: ERR.INVALID_PARAMS, message: 'path must be a non-empty string' };
  if (path.split(/[/\\]/).includes('..')) return { reason: 'path_traversal', code: ERR.SAFETY_BLOCKED, message: 'path traversal blocked', safety: true };
  let target;
  if (path.startsWith('/')) {
    target = normAbs(path);
    if (!inSandbox(target)) return { reason: 'absolute_path_blocked', code: ERR.SAFETY_BLOCKED, message: 'absolute path outside sandbox blocked', safety: true };
  } else {
    target = normAbs(SANDBOX_ROOT + '/' + path);
    if (!inSandbox(target)) return { reason: 'path_traversal', code: ERR.SAFETY_BLOCKED, message: 'path traversal blocked', safety: true };
  }
  const name = target.slice(SANDBOX_ROOT.length + 1);
  if (!Object.hasOwn(FIXTURE_FILES, name)) return { reason: 'file_not_found', code: ERR.NOT_FOUND, message: 'file not found' };
  return { content: FIXTURE_FILES[name] };
}

// One HTTP POST /mcp through the Deep pipeline.
// token: 'reader' | 'operator' | 'none' | 'wrong'. recordedQueries: Map sql -> recorded rows.
export function evaluate({ token, id = 1, method, tool, args }, recordedQueries = new Map()) {
  const params = method === 'tools/call' ? { name: tool, arguments: args } : undefined;
  const request = makeRequest(id, method, params);
  const body = pyJson(request);
  const bodyBytes = new TextEncoder().encode(body).length;
  const out = (http, response, stage, audit = null, extra = {}) => {
    const e = response.error;
    let category = 'success';
    if (http === 401) category = 'unauthenticated';
    else if (http === 403) category = 'role_blocked';
    else if (http === 413 || (e && SAFETY_REASONS.includes(e.data.reason))) category = 'safety_blocked';
    else if (e) category = 'error';
    return { http, category, reason: e ? e.data.reason : null, code: e ? e.code : null, response, stage, audit, request, bodyBytes, ...extra };
  };
  // 1. size cap on the declared Content-Length, before parsing or auth
  if (bodyBytes > MAX_BODY_BYTES) return out(413, err(null, ERR.TOO_LARGE, 'request too large', 'request_too_large'), 'size cap', { category: 'safety', reason: 'request_too_large', tool: null, role: null });
  // 2. bearer token, compared by hash on the server
  const role = token === 'reader' || token === 'operator' ? token : null;
  if (!role) {
    const t = typeof request.params.name === 'string' ? request.params.name : request.params.name ?? null;
    return out(401, err(id, ERR.UNAUTHENTICATED, 'missing or invalid bearer token', 'unauthenticated'), 'authentication', { category: 'auth', reason: 'unauthenticated', tool: t, role: null });
  }
  // 3. dispatch
  if (method === 'initialize') return out(200, ok(id, { capabilities: { tools: true }, protocolVersion: PROTOCOL_VERSION, role, server: 'mcp-toolkit-deep', transport: 'http' }), 'dispatch');
  if (method === 'tools/list') return out(200, ok(id, { tools: TOOL_DEFS.filter((d) => ROLE_TOOLS[role].includes(d.name)) }), 'dispatch');
  if (method !== 'tools/call') return out(200, err(id, ERR.METHOD_NOT_FOUND, 'method not found', 'method_not_found'), 'dispatch');
  // 4. intent classification, then role allowlist
  const safety = (reason, message, t, stage) => out(200, err(id, ERR.SAFETY_BLOCKED, message, reason), stage, { category: 'safety', reason, tool: t, role });
  if (WRITE_TOOLS.includes(tool)) return safety('write_blocked', 'write tools are not offered', tool, 'intent');
  if (DELETE_TOOLS.includes(tool)) return safety('delete_blocked', 'delete tools are not offered', tool, 'intent');
  if (!ALL_TOOLS.includes(tool)) return safety('unknown_tool', 'unknown tool', typeof tool === 'string' ? tool : null, 'intent');
  if (!ROLE_TOOLS[role].includes(tool)) return out(403, err(id, ERR.FORBIDDEN_ROLE, `role ${role} may not call ${tool}`, 'forbidden_role'), 'role allowlist', { category: 'authorization', reason: 'forbidden_role', tool, role });
  if (!isObj(args)) return out(200, err(id, ERR.INVALID_PARAMS, 'arguments must be an object', 'invalid_params'), 'arguments');
  // 5. per-tool checks, then the tool itself
  if (tool === 'read_file') {
    const v = readFileVerdict(args.path);
    if (v.safety) return safety(v.reason, v.message, 'read_file', 'path rules');
    if (v.reason) return out(200, err(id, v.code, v.message, v.reason), 'path rules');
    return out(200, ok(id, { content: v.content, path: args.path }), 'tool ran');
  }
  if (tool === 'list_files') return out(200, ok(id, { files: Object.keys(FIXTURE_FILES).sort() }), 'tool ran');
  if (tool === 'list_items') return out(200, ok(id, { rows: SEED_ROWS }), 'tool ran');
  if (tool === 'run_query') {
    const sql = args.sql;
    if (typeof sql !== 'string' || !sql.trim()) return out(200, err(id, ERR.INVALID_PARAMS, 'sql must be a non-empty string', 'invalid_params'), 'arguments');
    const reason = checkSql(sql);
    if (reason) return safety(reason, 'only a single read-only SELECT is allowed', 'run_query', 'SQL guard');
    const rows = recordedQueries.get(sql);
    return out(200, ok(id, rows ? { rows } : null), 'SQL guard', null, { executed: false, recordedRows: !!rows });
  }
  if (tool === 'calculate') {
    const { op, a, b } = args;
    if (!['add', 'subtract', 'multiply', 'divide'].includes(op)) return out(200, err(id, ERR.INVALID_PARAMS, 'op must be add, subtract, multiply, or divide', 'invalid_params'), 'arguments');
    if (typeof a !== 'number' || typeof b !== 'number') return out(200, err(id, ERR.INVALID_PARAMS, 'a and b must be numbers', 'invalid_params'), 'arguments');
    if (op === 'divide' && b === 0) return out(200, err(id, ERR.CALC, 'division by zero', 'calc_error'), 'tool ran');
    const value = op === 'add' ? a + b : op === 'subtract' ? a - b : op === 'multiply' ? a * b : a / b;
    return out(200, ok(id, { a, b, op, value }), 'tool ran');
  }
  // count_words
  if (typeof args.text !== 'string') return out(200, err(id, ERR.INVALID_PARAMS, 'text must be a string', 'invalid_params'), 'arguments');
  return out(200, ok(id, { count: args.text.split(/\s+/).filter(Boolean).length }), 'tool ran');
}

// Arguments for one entry of level-3-deep/deep_plan.json.
export const planArgs = (p) => (p.oversize_repeat ? { text: 'x '.repeat(p.oversize_repeat) } : p.arguments);
