import sys
import time
import inspect
import threading
import tracemalloc
import os
import gc
import ast
from functools import wraps
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class TraceStep:
    """Single execution step data."""
    timestamp: float
    line_no: int
    locals: Dict[str, Any]
    memory: int
    memory_delta: int
    peak_memory: int
    gc_counts: Tuple[int, int, int]
    event: str
    filename: str
    call_stack: List[Dict]
    exec_time_delta: float
    elapsed_time: float
    stmt_type: str = ''
    stmt_source: str = ''


@dataclass
class TraceResult:
    """Complete trace result."""
    success: bool = True
    steps: int = 0
    source: List[str] = field(default_factory=list)
    start_line: int = 1
    trace: List[Dict] = field(default_factory=list)
    output: List[Dict] = field(default_factory=list)
    hotspots: List[Tuple[int, int]] = field(default_factory=list)
    time_hotspots: List[Tuple[int, float]] = field(default_factory=list)
    total_exec_time: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            'success': self.success,
            'steps': self.steps,
            'source': self.source,
            'start_line': self.start_line,
            'trace': self.trace,
            'output': self.output,
            'hotspots': self.hotspots,
            'time_hotspots': self.time_hotspots,
            'total_exec_time': self.total_exec_time,
            'error': self.error,
        }


class LineMapper(ast.NodeVisitor):
    """Maps AST nodes to line numbers."""

    def __init__(self):
        self.mapping = {}

    def visit(self, node):
        if hasattr(node, 'lineno'):
            if isinstance(node, (ast.stmt, ast.Module)) or node.lineno not in self.mapping:
                self.mapping[node.lineno] = {
                    'type': type(node).__name__,
                    'source': ast.unparse(node).split('\n')[0] if hasattr(ast, 'unparse') else ""
                }
        self.generic_visit(node)


def analyze_ast(code_string: str) -> Dict:
    """Analyze Python code AST for structure context."""
    try:
        tree = ast.parse(code_string)
        mapper = LineMapper()
        mapper.visit(tree)
        return mapper.mapping
    except Exception:
        return {}


class StreamCapturer:
    """Captures stdout/stderr while preserving original stream."""

    def __init__(self, original_stream, output_list: List[Dict]):
        self.original_stream = original_stream
        self.output_list = output_list

    def write(self, message):
        timestamp = time.time()
        self.original_stream.write(message)
        if message:
            self.output_list.append({
                'timestamp': timestamp,
                'content': message
            })

    def flush(self):
        self.original_stream.flush()


def serialize(obj, depth=0, max_depth=3):
    """
    Serialize objects for JSON output.
    Handles basic types and complex structures with depth limiting.
    """
    if depth > max_depth:
        return "<Max Depth Reached>"

    if isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    elif isinstance(obj, (list, tuple)):
        try:
            if len(obj) > 100:
                return [serialize(item, depth + 1, max_depth) for item in obj[:100]] + ["<Truncated...>"]
            return [serialize(item, depth + 1, max_depth) for item in obj]
        except RecursionError:
            return "<Recursion detected>"
    elif isinstance(obj, dict):
        try:
            if len(obj) > 100:
                items = list(obj.items())[:100]
                serialized = {str(key): serialize(value, depth + 1, max_depth) for key, value in items}
                serialized["<Truncated...>"] = "..."
                return serialized
            return {str(key): serialize(value, depth + 1, max_depth) for key, value in obj.items()}
        except RecursionError:
            return "<Recursion detected>"
    elif hasattr(obj, '__dict__'):
        try:
            return {k: serialize(v, depth + 1, max_depth) for k, v in obj.__dict__.items() if not k.startswith('__')}
        except RecursionError:
            return "<Recursion detected>"
    else:
        try:
            return str(obj)
        except:
            return "<Unprintable Object>"


class TraceContext:
    """Thread-safe trace data context."""

    def __init__(self):
        self._lock = threading.Lock()
        self._trace_data: List[Dict] = []
        self._captured_output: List[Dict] = []
        self._call_stack: List[Dict] = []

    def clear(self):
        with self._lock:
            self._trace_data = []
            self._captured_output = []
            self._call_stack = []

    def add_trace_step(self, step: Dict):
        with self._lock:
            self._trace_data.append(step)

    def add_output(self, output: Dict):
        with self._lock:
            self._captured_output.append(output)

    def push_call(self, call_info: Dict):
        with self._lock:
            self._call_stack.append(call_info)

    def pop_call(self) -> Optional[Dict]:
        with self._lock:
            if self._call_stack:
                return self._call_stack.pop()
            return None

    def get_call_stack_copy(self) -> List[Dict]:
        with self._lock:
            return list(self._call_stack)

    @property
    def trace_data(self) -> List[Dict]:
        with self._lock:
            return list(self._trace_data)

    @property
    def captured_output(self) -> List[Dict]:
        with self._lock:
            return list(self._captured_output)


def trace_code(code_string: str, max_steps: int = 50000) -> TraceResult:
    """
    Trace execution of a code string with thread-safe data management.
    """
    context = TraceContext()
    result = TraceResult()

    # Pre-process source lines
    source_lines = [line + '\n' for line in code_string.splitlines()]
    result.source = source_lines
    result.start_line = 1

    # Analyze AST for structure context
    ast_mapping = analyze_ast(code_string)

    # Start tracking memory and time
    tracemalloc.start()
    start_time = time.perf_counter_ns()
    previous_time = start_time
    step_times: Dict[int, int] = {}
    step_count = 0

    def trace_func(frame, event, arg):
        nonlocal previous_time, step_count

        if step_count >= max_steps:
            return None

        filename = frame.f_code.co_filename

        # Only trace the executed string
        if filename != "<string>":
            return None

        # Handle function call events
        if event == 'call':
            context.push_call({
                'name': frame.f_code.co_name,
                'line': frame.f_lineno,
                'filename': filename
            })
            return trace_func

        # Handle function return events
        if event == 'return':
            context.pop_call()
            return trace_func

        if event == 'line':
            step_count += 1
            timestamp = time.time()
            current_perf = time.perf_counter_ns()
            line_no = frame.f_lineno

            # Calculate time delta
            exec_time_delta_ns = max(1, current_perf - previous_time)
            exec_time_delta = exec_time_delta_ns / 1_000_000_000.0
            previous_time = current_perf

            # Capture local variables
            locals_snapshot = {}
            for key, value in frame.f_locals.items():
                if key.startswith('__'):
                    continue
                try:
                    locals_snapshot[key] = serialize(value)
                except Exception as e:
                    locals_snapshot[key] = f"<Error serialization: {str(e)}>"

            # Capture memory
            current, peak = tracemalloc.get_traced_memory()
            gc_counts = gc.get_count()

            # Get AST context
            stmt_info = ast_mapping.get(line_no, {})
            stmt_type = stmt_info.get('type', 'Unknown')
            stmt_source = stmt_info.get('source', '')

            # Track time per line
            if line_no not in step_times:
                step_times[line_no] = 0
            step_times[line_no] += exec_time_delta_ns

            elapsed_ns = current_perf - start_time
            elapsed_seconds = elapsed_ns / 1_000_000_000.0

            context.add_trace_step({
                'timestamp': timestamp,
                'line_no': line_no,
                'locals': locals_snapshot,
                'memory': current,
                'memory_delta': 0,
                'peak_memory': peak,
                'gc_counts': gc_counts,
                'event': event,
                'filename': filename,
                'stmt_type': stmt_type,
                'stmt_source': stmt_source,
                'call_stack': context.get_call_stack_copy(),
                'exec_time_delta': exec_time_delta,
                'elapsed_time': elapsed_seconds
            })

        return trace_func

    sys.settrace(trace_func)
    original_stdout = sys.stdout
    sys.stdout = StreamCapturer(original_stdout, context._captured_output)

    try:
        exec(code_string, {'__name__': '__main__'})
        result.success = True
    except Exception as e:
        result.success = True  # Still return trace even with errors
        error_msg = str(e)
        context.add_output({
            'timestamp': time.time(),
            'content': f"\nError: {error_msg}"
        })
    finally:
        end_time = time.perf_counter_ns()
        total_exec_time = (end_time - start_time) / 1_000_000_000.0

        sys.stdout = original_stdout
        sys.settrace(None)
        tracemalloc.stop()

        # Get collected data
        trace_data = context.trace_data

        # Calculate memory deltas
        prev_memory = 0
        for step in trace_data:
            step['memory_delta'] = step['memory'] - prev_memory
            prev_memory = step['memory']

        # Process memory hotspots
        deltas = [(s['line_no'], s['memory_delta']) for s in trace_data if s['memory_delta'] > 0]
        deltas.sort(key=lambda x: x[1], reverse=True)
        result.hotspots = deltas[:5]

        # Process time hotspots
        time_hotspots_list = sorted(step_times.items(), key=lambda x: x[1], reverse=True)[:5]
        result.time_hotspots = [(line, t / 1_000_000_000.0) for line, t in time_hotspots_list]

        result.steps = len(trace_data)
        result.trace = trace_data
        result.output = context.captured_output
        result.total_exec_time = total_exec_time

    return result


def trace(func):
    """
    Decorator to record the execution of a function.
    Decoupled from web layer - returns trace data directly.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        context = TraceContext()

        # Get source code of the function
        try:
            source_lines, start_line = inspect.getsourcelines(func)
            func_file = inspect.getfile(func)
            project_root = os.path.dirname(os.path.abspath(func_file))
        except (OSError, TypeError):
            source_lines = []
            start_line = 0
            project_root = None

        # Start tracking
        tracemalloc.start()
        start_time = time.perf_counter()
        previous_time = start_time
        step_times: Dict[int, int] = {}

        def trace_func(frame, event, arg):
            nonlocal previous_time
            filename = frame.f_code.co_filename

            # Avoid tracing the tracer
            if 'chronotrace' in filename:
                return None

            # Only trace project files
            if project_root and not os.path.abspath(filename).startswith(project_root):
                return None

            if event == 'call':
                context.push_call({
                    'name': frame.f_code.co_name,
                    'line': frame.f_lineno,
                    'filename': filename
                })
                return trace_func

            if event == 'return':
                context.pop_call()
                return trace_func

            if event == 'line':
                timestamp = time.time()
                current_perf = time.perf_counter()
                line_no = frame.f_lineno
                exec_time_delta = current_perf - previous_time
                previous_time = current_perf

                # Capture locals
                locals_snapshot = {}
                for key, value in frame.f_locals.items():
                    if key.startswith('__'):
                        continue
                    try:
                        locals_snapshot[key] = serialize(value)
                    except Exception as e:
                        locals_snapshot[key] = f"<Error serialization: {str(e)}>"

                # Capture memory
                current, peak = tracemalloc.get_traced_memory()
                gc_counts = gc.get_count()

                context.add_trace_step({
                    'timestamp': timestamp,
                    'line_no': line_no,
                    'locals': locals_snapshot,
                    'memory': current,
                    'memory_delta': 0,
                    'peak_memory': peak,
                    'gc_counts': gc_counts,
                    'event': event,
                    'filename': filename,
                    'call_stack': context.get_call_stack_copy(),
                    'exec_time_delta': exec_time_delta,
                    'elapsed_time': current_perf - start_time
                })

            return trace_func

        sys.settrace(trace_func)
        original_stdout = sys.stdout
        sys.stdout = StreamCapturer(original_stdout, context._captured_output)

        result = None
        error = None

        try:
            result = func(*args, **kwargs)
        except Exception as e:
            error = e
            print(f"Exception during execution: {e}")
        finally:
            end_time = time.perf_counter()
            total_exec_time = end_time - start_time

            sys.stdout = original_stdout
            sys.settrace(None)
            tracemalloc.stop()

            # Calculate hotspots
            trace_data = context.trace_data
            deltas = [(s['line_no'], s.get('memory_delta', 0)) for s in trace_data if s.get('memory_delta', 0) > 0]
            deltas.sort(key=lambda x: x[1], reverse=True)
            hotspots = deltas[:5]

            # Time hotspots
            time_hotspots = {}
            for step in trace_data:
                line = step['line_no']
                t = step.get('exec_time_delta', 0)
                if line not in time_hotspots or t > time_hotspots[line]:
                    time_hotspots[line] = t
            time_hotspots_list = sorted(time_hotspots.items(), key=lambda x: x[1], reverse=True)[:5]

            # Store trace data on the wrapper for later access
            wrapper.trace_data = {
                'source': [line.rstrip('\n') for line in source_lines],
                'start_line': start_line,
                'trace': trace_data,
                'output': context.captured_output,
                'hotspots': hotspots,
                'time_hotspots': time_hotspots_list,
                'total_exec_time': total_exec_time
            }

            if error:
                raise error

        return result

    wrapper.trace_data = None
    return wrapper
