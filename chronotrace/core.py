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
class TraceResult:
    """Complete trace result."""
    success: bool = True
    had_error: bool = False
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
            'had_error': self.had_error,
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
    try:
        tree = ast.parse(code_string)
        mapper = LineMapper()
        mapper.visit(tree)
        return mapper.mapping
    except Exception:
        return {}


class StreamCapturer:
    def __init__(self, original_stream, output_list: List[Dict]):
        self.original_stream = original_stream
        self.output_list = output_list

    def write(self, message):
        timestamp = time.time()
        self.original_stream.write(message)
        if message:
            self.output_list.append({'timestamp': timestamp, 'content': message})

    def flush(self):
        self.original_stream.flush()


_MAX_SERIALIZE_ITEMS = 50
_MAX_SERIALIZE_DEPTH = 2


def serialize(obj, depth=0, max_depth=_MAX_SERIALIZE_DEPTH, seen=None):
    """
    Serialize objects for JSON output.
    seen: set of object ids to detect circular references (not id reuse).
    """
    if seen is None:
        seen = set()

    if depth > max_depth:
        return repr(obj)[:200] if not isinstance(obj, (int, float, str, bool, type(None))) else obj

    # Primitives don't need cycle detection
    if isinstance(obj, (int, float, str, bool, type(None))):
        return obj

    obj_id = id(obj)
    if obj_id in seen:
        return "<Circular reference>"
    seen.add(obj_id)

    try:
        if isinstance(obj, (list, tuple)):
            n = len(obj)
            if n > _MAX_SERIALIZE_ITEMS:
                result = [serialize(item, depth + 1, max_depth, seen) for item in obj[:_MAX_SERIALIZE_ITEMS]]
                result.append(f"<... {n - _MAX_SERIALIZE_ITEMS} more>")
                return result
            return [serialize(item, depth + 1, max_depth, seen) for item in obj]
        elif isinstance(obj, dict):
            n = len(obj)
            if n > _MAX_SERIALIZE_ITEMS:
                items = list(obj.items())[:_MAX_SERIALIZE_ITEMS]
                serialized = {str(k): serialize(v, depth + 1, max_depth, seen) for k, v in items}
                serialized["<...>"] = f"{n - _MAX_SERIALIZE_ITEMS} more"
                return serialized
            return {str(k): serialize(v, depth + 1, max_depth, seen) for k, v in obj.items()}
        elif hasattr(obj, '__dict__'):
            return {k: serialize(v, depth + 1, max_depth, seen) for k, v in list(obj.__dict__.items())[:_MAX_SERIALIZE_ITEMS] if not k.startswith('__')}
        else:
            return str(obj)[:200]
    except RecursionError:
        return "<Recursion detected>"
    except Exception:
        return "<Serialization error>"
    finally:
        seen.discard(obj_id)


class TraceContext:
    """Thread-safe trace data context with per-instance serialization cache."""

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

    def serialize(self, obj, depth=0):
        """Serialize object for JSON output."""
        return serialize(obj, depth)

    @property
    def trace_data(self) -> List[Dict]:
        with self._lock:
            return list(self._trace_data)

    @property
    def captured_output(self) -> List[Dict]:
        with self._lock:
            return list(self._captured_output)


def trace_code(code_string: str, max_steps: int = 50000) -> TraceResult:
    """Trace execution of a code string with thread-safe data management."""
    context = TraceContext()
    result = TraceResult()

    source_lines = [line + '\n' for line in code_string.splitlines()]
    result.source = source_lines
    result.start_line = 1

    ast_mapping = analyze_ast(code_string)

    tracemalloc.start()
    start_time = time.perf_counter_ns()
    previous_time = start_time
    previous_memory = 0  # Track memory delta correctly
    step_times: Dict[int, int] = {}
    step_count = 0

    def trace_func(frame, event, arg):
        nonlocal previous_time, previous_memory, step_count

        if step_count >= max_steps:
            return None

        filename = frame.f_code.co_filename
        if filename != "<string>":
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
            step_count += 1
            timestamp = time.time()
            current_perf = time.perf_counter_ns()
            line_no = frame.f_lineno

            exec_time_delta_ns = max(1, current_perf - previous_time)
            exec_time_delta = exec_time_delta_ns / 1_000_000_000.0
            previous_time = current_perf

            # Capture locals using context's cache
            locals_snapshot = {}
            for key, value in frame.f_locals.items():
                if key.startswith('__'):
                    continue
                try:
                    locals_snapshot[key] = context.serialize(value)
                except Exception as e:
                    locals_snapshot[key] = f"<Error: {str(e)}>"

            # Capture memory - compute actual delta
            current, peak = tracemalloc.get_traced_memory()
            memory_delta = current - previous_memory
            previous_memory = current
            gc_counts = gc.get_count()

            stmt_info = ast_mapping.get(line_no, {})
            stmt_type = stmt_info.get('type', 'Unknown')
            stmt_source = stmt_info.get('source', '')

            if line_no not in step_times:
                step_times[line_no] = 0
            step_times[line_no] += exec_time_delta_ns

            elapsed_seconds = (current_perf - start_time) / 1_000_000_000.0

            context.add_trace_step({
                'timestamp': timestamp,
                'line_no': line_no,
                'locals': locals_snapshot,
                'memory': current,
                'memory_delta': memory_delta,  # Now correctly computed
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
        result.had_error = False
    except Exception as e:
        result.success = True
        result.had_error = True
        result.error = str(e)
        context.add_output({'timestamp': time.time(), 'content': f"\nError: {str(e)}"})
    finally:
        end_time = time.perf_counter_ns()
        total_exec_time = (end_time - start_time) / 1_000_000_000.0

        sys.stdout = original_stdout
        sys.settrace(None)
        tracemalloc.stop()

        trace_data = context.trace_data

        # Memory hotspots - aggregate positive deltas by line
        line_memory: Dict[int, int] = {}
        for step in trace_data:
            delta = step.get('memory_delta', 0)
            if delta > 0:
                line = step['line_no']
                line_memory[line] = line_memory.get(line, 0) + delta
        sorted_lines = sorted(line_memory.items(), key=lambda x: x[1], reverse=True)
        result.hotspots = sorted_lines[:5]

        time_hotspots_list = sorted(step_times.items(), key=lambda x: x[1], reverse=True)[:5]
        result.time_hotspots = [(line, t / 1_000_000_000.0) for line, t in time_hotspots_list]

        result.steps = len(trace_data)
        result.trace = trace_data
        result.output = context.captured_output
        result.total_exec_time = total_exec_time

    return result


def trace(func):
    """Decorator to record the execution of a function."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        context = TraceContext()

        try:
            source_lines, start_line = inspect.getsourcelines(func)
            func_file = inspect.getfile(func)
            project_root = os.path.dirname(os.path.abspath(func_file))
        except (OSError, TypeError):
            source_lines = []
            start_line = 0
            project_root = None

        tracemalloc.start()
        start_time = time.perf_counter_ns()
        previous_time = start_time
        previous_memory = 0
        step_times: Dict[int, int] = {}

        def trace_func(frame, event, arg):
            nonlocal previous_time, previous_memory
            filename = frame.f_code.co_filename

            if 'chronotrace' in filename:
                return None
            if project_root and not os.path.abspath(filename).startswith(project_root):
                return None

            if event == 'call':
                context.push_call({'name': frame.f_code.co_name, 'line': frame.f_lineno, 'filename': filename})
                return trace_func
            if event == 'return':
                context.pop_call()
                return trace_func

            if event == 'line':
                timestamp = time.time()
                current_perf = time.perf_counter_ns()
                line_no = frame.f_lineno

                exec_time_delta_ns = max(1, current_perf - previous_time)
                exec_time_delta = exec_time_delta_ns / 1_000_000_000.0
                previous_time = current_perf

                if line_no not in step_times:
                    step_times[line_no] = 0
                step_times[line_no] += exec_time_delta_ns

                locals_snapshot = {}
                for key, value in frame.f_locals.items():
                    if key.startswith('__'):
                        continue
                    try:
                        locals_snapshot[key] = context.serialize(value)
                    except Exception as e:
                        locals_snapshot[key] = f"<Error: {str(e)}>"

                current, peak = tracemalloc.get_traced_memory()
                memory_delta = current - previous_memory
                previous_memory = current
                gc_counts = gc.get_count()

                context.add_trace_step({
                    'timestamp': timestamp,
                    'line_no': line_no,
                    'locals': locals_snapshot,
                    'memory': current,
                    'memory_delta': memory_delta,
                    'peak_memory': peak,
                    'gc_counts': gc_counts,
                    'event': event,
                    'filename': filename,
                    'call_stack': context.get_call_stack_copy(),
                    'exec_time_delta': exec_time_delta,
                    'elapsed_time': (current_perf - start_time) / 1_000_000_000.0
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
            end_time = time.perf_counter_ns()
            total_exec_time = (end_time - start_time) / 1_000_000_000.0

            sys.stdout = original_stdout
            sys.settrace(None)
            tracemalloc.stop()

            trace_data = context.trace_data

            line_memory: Dict[int, int] = {}
            for step in trace_data:
                delta = step.get('memory_delta', 0)
                if delta > 0:
                    line = step['line_no']
                    line_memory[line] = line_memory.get(line, 0) + delta
            sorted_lines = sorted(line_memory.items(), key=lambda x: x[1], reverse=True)
            hotspots = sorted_lines[:5]

            time_hotspots_list = sorted(step_times.items(), key=lambda x: x[1], reverse=True)[:5]
            time_hotspots_seconds = [(line, t / 1_000_000_000.0) for line, t in time_hotspots_list]

            wrapper.trace_data = {
                'source': [line.rstrip('\n') for line in source_lines],
                'start_line': start_line,
                'trace': trace_data,
                'output': context.captured_output,
                'hotspots': hotspots,
                'time_hotspots': time_hotspots_seconds,
                'total_exec_time': total_exec_time
            }

            if error:
                raise error

        return result

    wrapper.trace_data = None
    return wrapper
