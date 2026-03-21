"""
ChronoTrace Web Application
Flask-based web interface for code execution tracing.
"""
from flask import Flask, render_template, jsonify, send_from_directory, request
import json
import os
import sys
import time
import platform
import threading
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict

# Ensure we can import from parent directory
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
root_dir = os.path.dirname(parent_dir)

if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from chronotrace.sandbox import validate_code_safety, trace_code_sandboxed
from chronotrace.core import trace_code

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

# On Windows/Mac, subprocess spawn is slow; use direct tracing
_USE_SUBPROCESS = platform.system() not in ('Windows', 'Darwin')


# ==================== Rate Limiter ====================

class RateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        self._lock = threading.Lock()
        self._max_requests = max_requests
        self._window = window_seconds
        self._requests: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, client_id: str) -> bool:
        now = time.time()
        with self._lock:
            # Clean old entries
            self._requests[client_id] = [
                t for t in self._requests[client_id]
                if now - t < self._window
            ]
            if len(self._requests[client_id]) >= self._max_requests:
                return False
            self._requests[client_id].append(now)
            return True

    def get_remaining(self, client_id: str) -> int:
        now = time.time()
        with self._lock:
            recent = [t for t in self._requests[client_id] if now - t < self._window]
            return max(0, self._max_requests - len(recent))


# Rate limiters: 30 requests/min for run, 120/min for others
run_limiter = RateLimiter(max_requests=30, window_seconds=60)
api_limiter = RateLimiter(max_requests=120, window_seconds=60)


def get_client_ip() -> str:
    """Get client IP, respecting proxies."""
    return request.headers.get('X-Forwarded-For', request.remote_addr)


# ==================== SQLite Persistence ====================

DB_PATH = os.path.join(root_dir, 'data', 'chronotrace.db')


def init_db():
    """Initialize SQLite database."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS executions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL NOT NULL,
            code_hash TEXT NOT NULL,
            steps INTEGER NOT NULL,
            peak_memory INTEGER NOT NULL,
            total_exec_time REAL NOT NULL,
            success INTEGER NOT NULL,
            had_error INTEGER NOT NULL,
            error TEXT,
            source_preview TEXT,
            data_json TEXT NOT NULL
        )
    ''')
    conn.execute('''
        CREATE INDEX IF NOT EXISTS idx_timestamp ON executions(timestamp)
    ''')
    conn.commit()
    conn.close()


def save_execution(data: Dict) -> int:
    """Save execution to database, return row id."""
    import hashlib
    conn = sqlite3.connect(DB_PATH)
    try:
        source = data.get('source', [])
        code_hash = hashlib.md5(''.join(source).encode()).hexdigest()[:16]
        trace = data.get('trace', [])
        peak_mem = max((s.get('memory', 0) for s in trace), default=0)

        cursor = conn.execute('''
            INSERT INTO executions
            (timestamp, code_hash, steps, peak_memory, total_exec_time,
             success, had_error, error, source_preview, data_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            time.time(),
            code_hash,
            len(trace),
            peak_mem,
            data.get('total_exec_time', 0),
            1 if data.get('success') else 0,
            1 if data.get('had_error') else 0,
            data.get('error'),
            source[0][:100] if source else '',
            json.dumps(data)
        ))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def load_executions(limit: int = 50) -> List[Dict]:
    """Load recent executions from database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            'SELECT id, timestamp, steps, peak_memory, total_exec_time, '
            'success, had_error, source_preview FROM executions '
            'ORDER BY id DESC LIMIT ?', (limit,)
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def load_execution(entry_id: int) -> Optional[Dict]:
    """Load single execution by id."""
    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute(
            'SELECT data_json FROM executions WHERE id = ?', (entry_id,)
        ).fetchone()
        if row:
            return json.loads(row[0])
        return None
    finally:
        conn.close()


# ==================== In-Memory Store ====================

class ExecutionStore:
    """Thread-safe in-memory storage (fast access to latest)."""

    def __init__(self, max_history: int = 20):
        self._lock = threading.Lock()
        self._trace_data: Optional[Dict] = None
        self._history: List[Dict] = []
        self._max_history = max_history

    def set_trace_data(self, data: Dict):
        with self._lock:
            self._trace_data = data
            if data and data.get('trace'):
                peak_mem = max(
                    [s.get('memory', 0) for s in data.get('trace', [])],
                    default=0
                )
                source = data.get('source', [])
                entry = {
                    'id': len(self._history) + 1,
                    'timestamp': time.time(),
                    'steps': len(data.get('trace', [])),
                    'source_preview': source[0][:60] if source else '',
                    'peak_memory': peak_mem,
                    'hotspots': data.get('hotspots', []),
                    'data': data
                }
                self._history.append(entry)
                if len(self._history) > self._max_history:
                    self._history = self._history[-self._max_history:]

    def get_trace_data(self) -> Optional[Dict]:
        with self._lock:
            return self._trace_data

    def get_history(self) -> List[Dict]:
        with self._lock:
            return list(self._history)

    def get_history_entry(self, entry_id: int) -> Optional[Dict]:
        with self._lock:
            for entry in self._history:
                if entry['id'] == entry_id:
                    return entry['data']
            return None


# Initialize
init_db()
store = ExecutionStore()

VERSION_INFO = {
    'branch': os.environ.get('CHRONOTRACE_GIT_BRANCH', 'unknown'),
    'commit': os.environ.get('CHRONOTRACE_GIT_COMMIT', 'unknown'),
}


def get_version_info() -> Dict[str, str]:
    return VERSION_INFO.copy()


# ==================== Middleware ====================

@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

    if '/static/' in request.path:
        response.headers['Cache-Control'] = 'public, max-age=86400'
    elif request.path.endswith('.html') or request.path == '/' or '/api/' in request.path:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'

    return response


# ==================== Page Routes ====================

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/source')
def source_view():
    return render_template('source.html')


@app.route('/editor')
def editor_view():
    return render_template('editor.html')


@app.route('/memory')
def memory_view():
    return render_template('memory.html')


@app.route('/settings')
def settings_view():
    return render_template('settings.html')


@app.route('/visualizer')
def visualizer_view():
    return render_template('visualizer.html')


@app.route('/compare')
def compare_view():
    return render_template('compare.html')


@app.route('/favicon.ico')
def favicon():
    return "", 204


# ==================== API Routes ====================

@app.route('/api/v1/status')
def get_status():
    version_info = get_version_info()

    env = 'local'
    if os.environ.get('DOCKER'):
        env = 'docker'
    elif os.environ.get('WSL_DISTRO_NAME'):
        env = f"WSL: {os.environ.get('WSL_DISTRO_NAME')}"
    elif platform.system() == 'Linux':
        env = 'linux'
    elif platform.system() == 'Darwin':
        env = 'macos'
    elif platform.system() == 'Windows':
        env = 'windows'

    return jsonify({
        'status': 'online',
        'version': 'v1',
        'env': env,
        'branch': version_info['branch'],
        'commit': version_info['commit'],
        'python_version': platform.python_version(),
        'platform': platform.platform(),
        'project': 'ChronoTrace',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/v1/trace')
def get_trace():
    if not api_limiter.is_allowed(get_client_ip()):
        return jsonify({'error': 'Rate limit exceeded'}), 429
    data = store.get_trace_data()
    return jsonify(data or {})


@app.route('/api/v1/history')
def get_history():
    if not api_limiter.is_allowed(get_client_ip()):
        return jsonify({'error': 'Rate limit exceeded'}), 429

    # Combine in-memory and database history
    mem_history = store.get_history()
    db_history = load_executions(limit=30)

    summary = []
    seen_ids = set()

    for entry in mem_history:
        summary.append({
            'id': entry['id'],
            'timestamp': entry['timestamp'],
            'steps': entry['steps'],
            'source_preview': entry['source_preview'],
            'peak_memory': entry['peak_memory'],
            'hotspots_count': len(entry.get('hotspots', []))
        })
        seen_ids.add(entry['id'])

    for entry in db_history:
        if entry['id'] not in seen_ids:
            summary.append({
                'id': entry['id'],
                'timestamp': entry['timestamp'],
                'steps': entry['steps'],
                'source_preview': entry.get('source_preview', ''),
                'peak_memory': entry['peak_memory'],
                'hotspots_count': 0
            })

    return jsonify(summary[:50])


@app.route('/api/v1/history/<int:entry_id>')
def get_history_entry(entry_id):
    if not api_limiter.is_allowed(get_client_ip()):
        return jsonify({'error': 'Rate limit exceeded'}), 429

    # Try memory first, then database
    data = store.get_history_entry(entry_id)
    if not data:
        data = load_execution(entry_id)

    if data:
        return jsonify(data)
    return jsonify({'error': 'Entry not found'}), 404


@app.route('/api/v1/compare', methods=['POST'])
def compare_executions():
    if not api_limiter.is_allowed(get_client_ip()):
        return jsonify({'error': 'Rate limit exceeded'}), 429

    data = request.json
    if not data:
        return jsonify({'error': 'Invalid request'}), 400

    id_a = data.get('id_a')
    id_b = data.get('id_b')

    entry_a = store.get_history_entry(id_a) or load_execution(id_a)
    entry_b = store.get_history_entry(id_b) or load_execution(id_b)

    if not entry_a or not entry_b:
        return jsonify({'error': 'One or both entries not found'}), 404

    trace_a = entry_a.get('trace', [])
    trace_b = entry_b.get('trace', [])
    source_a = entry_a.get('source', [])
    source_b = entry_b.get('source', [])

    result = {
        'execution_a': {
            'id': id_a,
            'steps': len(trace_a),
            'source': source_a,
            'peak_memory': max((s.get('memory', 0) for s in trace_a), default=0),
            'hotspots': entry_a.get('hotspots', [])
        },
        'execution_b': {
            'id': id_b,
            'steps': len(trace_b),
            'source': source_b,
            'peak_memory': max((s.get('memory', 0) for s in trace_b), default=0),
            'hotspots': entry_b.get('hotspots', [])
        },
        'diff': compute_diff(trace_a, trace_b, source_a, source_b)
    }

    return jsonify(result)


@app.route('/api/v1/run', methods=['POST'])
def run_code():
    """Execute code with tracing."""
    client_ip = get_client_ip()

    # Rate limiting
    if not run_limiter.is_allowed(client_ip):
        remaining = run_limiter.get_remaining(client_ip)
        return jsonify({
            'success': False,
            'error': 'Rate limit exceeded. Please wait before retrying.',
            'retry_after': 60
        }), 429

    data = request.json
    if not data:
        return jsonify({'success': False, 'error': 'Invalid request'}), 400

    code = data.get('code')
    if not code:
        return jsonify({'success': False, 'error': 'No code provided'}), 400

    if len(code) > 50000:
        return jsonify({'success': False, 'error': 'Code exceeds maximum length (50000 chars)'}), 400

    # Validate code safety
    safety_error = validate_code_safety(code)
    if safety_error:
        return jsonify({
            'success': False,
            'error': f'Security check failed: {safety_error}'
        }), 403

    try:
        if _USE_SUBPROCESS:
            result = trace_code_sandboxed(code, max_steps=50000, timeout=30)

            if result.get('timed_out'):
                return jsonify({
                    'success': False,
                    'error': 'Execution timed out (30s limit). Possible infinite loop or too many iterations.',
                    'timed_out': True,
                    'hint': 'Try reducing loop iterations or adding break conditions.'
                }), 408

            result_dict = result
        else:
            trace_result = trace_code(code, max_steps=50000)
            result_dict = trace_result.to_dict()

        if result_dict.get('success') or result_dict.get('had_error'):
            # Save to memory and database
            store.set_trace_data(result_dict)
            save_execution(result_dict)
            return jsonify(result_dict)
        else:
            error_msg = result_dict.get('error', 'Unknown error')
            return jsonify({'success': False, 'error': error_msg}), 500

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== Helper Functions ====================

def compute_diff(trace_a, trace_b, source_a, source_b):
    diff_result = {
        'source_changed': source_a != source_b,
        'steps_diff': len(trace_b) - len(trace_a),
        'memory_diff': {},
        'line_coverage': {},
        'variable_changes': [],
        'execution_path_diff': []
    }

    mem_a = [s.get('memory', 0) for s in trace_a]
    mem_b = [s.get('memory', 0) for s in trace_b]
    peak_a = max(mem_a) if mem_a else 0
    peak_b = max(mem_b) if mem_b else 0
    diff_result['memory_diff'] = {
        'peak_a': peak_a,
        'peak_b': peak_b,
        'peak_delta': peak_b - peak_a,
        'avg_a': sum(mem_a) / len(mem_a) if mem_a else 0,
        'avg_b': sum(mem_b) / len(mem_b) if mem_b else 0
    }

    lines_a = set(s.get('line_no') for s in trace_a)
    lines_b = set(s.get('line_no') for s in trace_b)
    diff_result['line_coverage'] = {
        'lines_a': sorted(list(lines_a)),
        'lines_b': sorted(list(lines_b)),
        'only_in_a': sorted(list(lines_a - lines_b)),
        'only_in_b': sorted(list(lines_b - lines_a)),
        'common': sorted(list(lines_a & lines_b))
    }

    path_a = [s.get('line_no') for s in trace_a]
    path_b = [s.get('line_no') for s in trace_b]
    diff_result['execution_path_diff'] = compare_paths(path_a, path_b)

    if trace_a and trace_b:
        locals_a = trace_a[-1].get('locals', {})
        locals_b = trace_b[-1].get('locals', {})
        all_keys = set(list(locals_a.keys()) + list(locals_b.keys()))
        for key in sorted(all_keys):
            if key.startswith('__'):
                continue
            val_a = locals_a.get(key, '<undefined>')
            val_b = locals_b.get(key, '<undefined>')
            if val_a != val_b:
                diff_result['variable_changes'].append({
                    'name': key,
                    'value_a': val_a,
                    'value_b': val_b
                })

    return diff_result


def compare_paths(path_a, path_b):
    result = {
        'total_steps_a': len(path_a),
        'total_steps_b': len(path_b),
        'common_prefix_len': 0,
        'divergence_points': [],
        'unique_lines_a': [],
        'unique_lines_b': []
    }

    min_len = min(len(path_a), len(path_b))
    for i in range(min_len):
        if path_a[i] == path_b[i]:
            result['common_prefix_len'] += 1
        else:
            break

    set_a = set(path_a)
    set_b = set(path_b)
    result['unique_lines_a'] = sorted(list(set_a - set_b))
    result['unique_lines_b'] = sorted(list(set_b - set_a))

    if result['common_prefix_len'] < min_len:
        result['divergence_points'].append({
            'step': result['common_prefix_len'],
            'line_a': path_a[result['common_prefix_len']],
            'line_b': path_b[result['common_prefix_len']]
        })

    return result


# ==================== Startup ====================

def start_server(port=5000):
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug_mode, use_reloader=False, port=port)


if __name__ == '__main__':
    start_server()
