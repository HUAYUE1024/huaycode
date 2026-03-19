from flask import Flask, render_template, jsonify, send_from_directory, request
import json
import os
import sys
import time

# Ensure we can import from parent directory
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir) # chronotrace
root_dir = os.path.dirname(parent_dir) # E:\111
sys.path.append(root_dir)

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

# API Version
API_VERSION = 'v1'

TRACE_DATA = {}
EXECUTION_HISTORY = []
MAX_HISTORY = 20


@app.after_request
def add_security_headers(response):
    # Security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Cache static assets
    if '/static/' in request.path:
        response.headers['Cache-Control'] = 'public, max-age=86400'  # 24 hours
    
    return response


def set_trace_data(data):
    global TRACE_DATA, EXECUTION_HISTORY
    TRACE_DATA = data
    # Save to history
    if data and data.get('trace'):
        peak_mem = max([s.get('memory', 0) for s in data.get('trace', [])], default=0)
        source = data.get('source', [])
        entry = {
            'id': len(EXECUTION_HISTORY) + 1,
            'timestamp': time.time(),
            'steps': len(data.get('trace', [])),
            'source_preview': source[0][:60] if source else '',
            'peak_memory': peak_mem,
            'hotspots': data.get('hotspots', []),
            'data': data
        }
        EXECUTION_HISTORY.append(entry)
        # Keep only last MAX_HISTORY entries
        if len(EXECUTION_HISTORY) > MAX_HISTORY:
            EXECUTION_HISTORY = EXECUTION_HISTORY[-MAX_HISTORY:]


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


@app.route('/api/status')
def get_status():
    return jsonify({
        'status': 'online',
        'version': API_VERSION,
        'env': 'WSL: Ubuntu',
        'branch': 'main',
        'python_version': '3.12.0',
        'project': 'HUAYCODE'
    })


@app.route('/api/v1/trace')
@app.route('/api/trace')
def get_trace():
    return jsonify(TRACE_DATA)


@app.route('/api/v1/history')
@app.route('/api/history')
def get_history():
    # Return history without full data payload
    summary = []
    for entry in EXECUTION_HISTORY:
        summary.append({
            'id': entry['id'],
            'timestamp': entry['timestamp'],
            'steps': entry['steps'],
            'source_preview': entry['source_preview'],
            'peak_memory': entry['peak_memory'],
            'hotspots_count': len(entry.get('hotspots', []))
        })
    return jsonify(summary)


@app.route('/api/history/<int:entry_id>')
def get_history_entry(entry_id):
    for entry in EXECUTION_HISTORY:
        if entry['id'] == entry_id:
            return jsonify(entry['data'])
    return jsonify({'error': 'Entry not found'}), 404


@app.route('/api/compare', methods=['POST'])
def compare_executions():
    data = request.json
    id_a = data.get('id_a')
    id_b = data.get('id_b')

    entry_a = None
    entry_b = None

    for entry in EXECUTION_HISTORY:
        if entry['id'] == id_a:
            entry_a = entry
        if entry['id'] == id_b:
            entry_b = entry

    if not entry_a or not entry_b:
        return jsonify({'error': 'One or both entries not found'}), 404

    trace_a = entry_a['data'].get('trace', [])
    trace_b = entry_b['data'].get('trace', [])
    source_a = entry_a['data'].get('source', [])
    source_b = entry_b['data'].get('source', [])

    # Build comparison result
    result = {
        'execution_a': {
            'id': entry_a['id'],
            'timestamp': entry_a['timestamp'],
            'steps': len(trace_a),
            'source': source_a,
            'peak_memory': entry_a['peak_memory'],
            'hotspots': entry_a['data'].get('hotspots', [])
        },
        'execution_b': {
            'id': entry_b['id'],
            'timestamp': entry_b['timestamp'],
            'steps': len(trace_b),
            'source': source_b,
            'peak_memory': entry_b['peak_memory'],
            'hotspots': entry_b['data'].get('hotspots', [])
        },
        'diff': compute_diff(trace_a, trace_b, source_a, source_b)
    }

    return jsonify(result)


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
    lines_a = set()
    lines_b = set()
    for step in trace_a:
        lines_a.add(step.get('line_no'))
    for step in trace_b:
        lines_b.add(step.get('line_no'))

    diff_result['line_coverage'] = {
        'lines_a': sorted(list(lines_a)),
        'lines_b': sorted(list(lines_b)),
        'only_in_a': sorted(list(lines_a - lines_b)),
        'only_in_b': sorted(list(lines_b - lines_a)),
        'common': sorted(list(lines_a & lines_b))
    }

    # Execution path comparison (sequence of line numbers)
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


@app.route('/api/run', methods=['POST'])
def run_code():
    data = request.json
    if not data:
        return jsonify({'error': '无效请求', 'code': 400}), 400
    
    code = data.get('code')
    if not code:
        return jsonify({'error': '未提供代码', 'code': 400}), 400
    
    if len(code) > 50000:
        return jsonify({'error': '代码长度超过限制 (最大 50000 字符)', 'code': 400}), 400

    try:
        # Dynamic import to handle path issues
        import sys
        if root_dir not in sys.path:
            sys.path.append(root_dir)

        # Import core module directly from file path if package import fails
        try:
            from chronotrace.core import trace_code
        except ImportError:
            import importlib.util
            spec = importlib.util.spec_from_file_location("chronotrace.core", os.path.join(parent_dir, "core.py"))
            core = importlib.util.module_from_spec(spec)
            sys.modules["chronotrace.core"] = core
            spec.loader.exec_module(core)
            trace_code = core.trace_code

        result = trace_code(code)
        set_trace_data(result)
        
        # Debug: print timing info
        if result.get('trace') and len(result['trace']) > 0:
            first_step = result['trace'][0]
            last_step = result['trace'][-1]
            
            # Check if timing data exists and has valid values
            elapsed_first = first_step.get('elapsed_time', 'MISSING')
            elapsed_last = last_step.get('elapsed_time', 'MISSING')
        
        return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/favicon.ico')
def favicon():
    return "", 204


def start_server(port=5000):
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug_mode, use_reloader=False, port=port)


if __name__ == '__main__':
    start_server()
