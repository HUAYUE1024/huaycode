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
from datetime import datetime
from typing import Dict, List, Optional

# Ensure we can import from parent directory
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)  # chronotrace
root_dir = os.path.dirname(parent_dir)  # project root

if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from chronotrace.sandbox import validate_code_safety, trace_code_sandboxed

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True


class ExecutionStore:
    """Thread-safe storage for execution history and trace data."""

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


# Initialize store
store = ExecutionStore()

# Version info - injected at build time via environment variables
# Set CHRONOTRACE_GIT_BRANCH and CHRONOTRACE_GIT_COMMIT before starting
VERSION_INFO = {
    'branch': os.environ.get('CHRONOTRACE_GIT_BRANCH', 'unknown'),
    'commit': os.environ.get('CHRONOTRACE_GIT_COMMIT', 'unknown'),
}


def get_version_info() -> Dict[str, str]:
    """Get version info from environment (injected at build time)."""
    return VERSION_INFO.copy()


@app.after_request
def add_security_headers(response):
    """Add security headers to all responses."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

    if '/static/' in request.path:
        response.headers['Cache-Control'] = 'public, max-age=86400'

    return response


# Page routes
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


# API v1 routes (canonical)
@app.route('/api/v1/status')
def get_status():
    """Get server status with dynamic system information."""
    version_info = get_version_info()

    # Detect environment
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
    """Get current trace data."""
    data = store.get_trace_data()
    return jsonify(data or {})


@app.route('/api/v1/history')
def get_history():
    """Get execution history summary."""
    history = store.get_history()
    summary = []
    for entry in history:
        summary.append({
            'id': entry['id'],
            'timestamp': entry['timestamp'],
            'steps': entry['steps'],
            'source_preview': entry['source_preview'],
            'peak_memory': entry['peak_memory'],
            'hotspots_count': len(entry.get('hotspots', []))
        })
    return jsonify(summary)


@app.route('/api/v1/history/<int:entry_id>')
def get_history_entry(entry_id):
    """Get specific history entry with full data."""
    data = store.get_history_entry(entry_id)
    if data:
        return jsonify(data)
    return jsonify({'error': 'Entry not found'}), 404


@app.route('/api/v1/compare', methods=['POST'])
def compare_executions():
    """Compare two execution traces."""
    data = request.json
    if not data:
        return jsonify({'error': 'Invalid request'}), 400

    id_a = data.get('id_a')
    id_b = data.get('id_b')

    entry_a = store.get_history_entry(id_a)
    entry_b = store.get_history_entry(id_b)

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
    """Execute code with tracing in sandboxed subprocess."""
    data = request.json
    if not data:
        return jsonify({'success': False, 'error': 'Invalid request'}), 400

    code = data.get('code')
    if not code:
        return jsonify({'success': False, 'error': 'No code provided'}), 400

    if len(code) > 50000:
        return jsonify({'success': False, 'error': 'Code exceeds maximum length (50000 chars)'}), 400

    # Validate code safety first
    safety_error = validate_code_safety(code)
    if safety_error:
        return jsonify({
            'success': False,
            'error': f'Security check failed: {safety_error}'
        }), 403

    try:
        # Execute in sandboxed subprocess - isolates sys.settrace/sys.stdout
        result = trace_code_sandboxed(code, max_steps=50000, timeout=30)

        if result.get('success') or result.get('had_error'):
            store.set_trace_data(result)
            return jsonify(result)
        else:
            error_msg = result.get('error', 'Unknown error')
            return jsonify({'error': error_msg}), 500

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def compute_diff(trace_a, trace_b, source_a, source_b):
    """Compute differences between two execution traces."""
    diff_result = {
        'source_changed': source_a != source_b,
        'steps_diff': len(trace_b) - len(trace_a),
        'memory_diff': {},
        'line_coverage': {},
        'variable_changes': [],
        'execution_path_diff': []
    }

    # Memory comparison
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

    # Line coverage comparison
    lines_a = set(s.get('line_no') for s in trace_a)
    lines_b = set(s.get('line_no') for s in trace_b)

    diff_result['line_coverage'] = {
        'lines_a': sorted(list(lines_a)),
        'lines_b': sorted(list(lines_b)),
        'only_in_a': sorted(list(lines_a - lines_b)),
        'only_in_b': sorted(list(lines_b - lines_a)),
        'common': sorted(list(lines_a & lines_b))
    }

    # Execution path comparison
    path_a = [s.get('line_no') for s in trace_a]
    path_b = [s.get('line_no') for s in trace_b]
    diff_result['execution_path_diff'] = compare_paths(path_a, path_b)

    # Final variable state comparison
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
    """Compare two execution paths and find divergences."""
    result = {
        'total_steps_a': len(path_a),
        'total_steps_b': len(path_b),
        'common_prefix_len': 0,
        'divergence_points': [],
        'unique_lines_a': [],
        'unique_lines_b': []
    }

    # Find common prefix
    min_len = min(len(path_a), len(path_b))
    for i in range(min_len):
        if path_a[i] == path_b[i]:
            result['common_prefix_len'] += 1
        else:
            break

    # Find unique execution lines
    set_a = set(path_a)
    set_b = set(path_b)
    result['unique_lines_a'] = sorted(list(set_a - set_b))
    result['unique_lines_b'] = sorted(list(set_b - set_a))

    # Find first divergence point
    if result['common_prefix_len'] < min_len:
        result['divergence_points'].append({
            'step': result['common_prefix_len'],
            'line_a': path_a[result['common_prefix_len']],
            'line_b': path_b[result['common_prefix_len']]
        })

    return result


# Legacy API routes (deprecated, redirect to v1)
@app.route('/api/trace')
def legacy_get_trace():
    return get_trace()


@app.route('/api/history')
def legacy_get_history():
    return get_history()


@app.route('/api/run', methods=['POST'])
def legacy_run_code():
    return run_code()


def start_server(port=5000):
    """Start the Flask development server."""
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug_mode, use_reloader=False, port=port)


if __name__ == '__main__':
    start_server()
