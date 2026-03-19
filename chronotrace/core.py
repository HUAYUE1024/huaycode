import sys
import time
import inspect
import json
import threading
import webbrowser
import tracemalloc
import os
import gc
import ast
from functools import wraps

# Global storage for the trace data
TRACE_DATA = []
CAPTURED_OUTPUT = []
CALL_STACK = []  # Function call stack tracking

class LineMapper(ast.NodeVisitor):
    def __init__(self):
        self.mapping = {}

    def visit(self, node):
        # Prioritize statements over expressions for the same line
        if hasattr(node, 'lineno'):
            # Only record if it's a statement or if we don't have an entry yet
            if isinstance(node, (ast.stmt, ast.Module)) or node.lineno not in self.mapping:
                self.mapping[node.lineno] = {
                    'type': type(node).__name__,
                    'source': ast.unparse(node).split('\n')[0] if hasattr(ast, 'unparse') else ""
                }
        self.generic_visit(node)

def analyze_ast(code_string):
    try:
        tree = ast.parse(code_string)
        mapper = LineMapper()
        mapper.visit(tree)
        return mapper.mapping
    except Exception:
        return {}


class StreamCapturer:
    def __init__(self, original_stream):
        self.original_stream = original_stream
        
    def write(self, message):
        timestamp = time.time()
        # Write to original stream
        self.original_stream.write(message)
        # Capture
        if message:
            CAPTURED_OUTPUT.append({
                'timestamp': timestamp,
                'content': message
            })
            
    def flush(self):
        self.original_stream.flush()

def serialize(obj, depth=0, max_depth=3):
    """
    Helper function to serialize objects for JSON.
    Handles basic types and some complex structures.
    """
    if depth > max_depth:
        return "<Max Depth Reached>"

    if isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    elif isinstance(obj, (list, tuple)):
        try:
            # Limit list size to avoid massive JSON payloads
            if len(obj) > 100:
                return [serialize(item, depth + 1, max_depth) for item in obj[:100]] + ["<Truncated...>"]
            return [serialize(item, depth + 1, max_depth) for item in obj]
        except RecursionError:
            return "<Recursion detected>"
    elif isinstance(obj, dict):
        try:
            # Limit dict size
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

def trace(func):
    """
    Decorator to record the execution of a function.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Local import to avoid circular dependency
        from .web.app import start_server, set_trace_data
        
        global TRACE_DATA, CAPTURED_OUTPUT, CALL_STACK
        TRACE_DATA = [] # Reset trace data
        CAPTURED_OUTPUT = [] # Reset output
        CALL_STACK = [] # Reset call stack
        
        # Get source code of the function
        try:
            source_lines, start_line = inspect.getsourcelines(func)
            func_file = inspect.getfile(func)
            project_root = os.path.dirname(os.path.abspath(func_file))
        except (OSError, TypeError):
            source_lines = []
            start_line = 0
            project_root = None
            
        # Start tracking memory and time
        tracemalloc.start()
        start_time = time.perf_counter()
        previous_memory = 0
        previous_time = start_time
        
        # Track heavy memory allocations
        memory_deltas = []

        def trace_func(frame, event, arg):
            nonlocal previous_memory, previous_time
            filename = frame.f_code.co_filename
            
            # Avoid tracing the tracer itself or internal modules
            if 'chronotrace' in filename:
                return None
            
            # Only trace files within the project root if determined
            # This filters out standard library and site-packages calls
            if project_root and not os.path.abspath(filename).startswith(project_root):
                return None
            
            # Handle function call events
            if event == 'call':
                func_name = frame.f_code.co_name
                CALL_STACK.append({
                    'name': func_name,
                    'line': frame.f_lineno,
                    'filename': filename
                })
                return trace_func
            
            # Handle function return events
            if event == 'return':
                if CALL_STACK:
                    CALL_STACK.pop()
                return trace_func
                
            if event == 'line':
                # Capture current state
                timestamp = time.time()
                current_perf = time.perf_counter()
                line_no = frame.f_lineno
                exec_time_delta = current_perf - previous_time
                previous_time = current_perf
                
                # Capture local variables
                locals_snapshot = {}
                # Only capture user variables, skip internal ones if possible
                for key, value in frame.f_locals.items():
                    if key.startswith('__'): continue
                    try:
                        locals_snapshot[key] = serialize(value)
                    except Exception as e:
                        locals_snapshot[key] = f"<Error serialization: {str(e)}>"
                
                # Capture memory usage
                current, peak = tracemalloc.get_traced_memory()
                memory_delta = current - previous_memory
                previous_memory = current

                # Garbage Collection stats (simple count)
                gc_counts = gc.get_count()

                TRACE_DATA.append({
                    'timestamp': timestamp,
                    'line_no': line_no,
                    'locals': locals_snapshot,
                    'memory': current,
                    'memory_delta': memory_delta,
                    'peak_memory': peak,
                    'gc_counts': gc_counts,
                    'event': event,
                    'filename': filename,
                    'call_stack': list(CALL_STACK),  # Copy current call stack
                    'exec_time_delta': exec_time_delta,  # Time since last line
                    'elapsed_time': current_perf - start_time  # Total elapsed time
                })
            return trace_func

        # Set the trace function
        sys.settrace(trace_func)
        
        # Capture stdout
        original_stdout = sys.stdout
        sys.stdout = StreamCapturer(original_stdout)
        
        try:
            result = func(*args, **kwargs)
        except Exception as e:
            print(f"Exception during execution: {e}")
            raise e
        finally:
            # Calculate total execution time
            end_time = time.perf_counter()
            total_exec_time = end_time - start_time
            
            # Restore stdout
            sys.stdout = original_stdout
            
            # Remove the trace function
            sys.settrace(None)
            tracemalloc.stop()
            
            print(f"ChronoTrace: Recording complete. {len(TRACE_DATA)} steps captured.")
            
            # Calculate hotspots (top 5 memory consumers)
            # Filter positive deltas only
            deltas = [(step['line_no'], step['memory_delta']) for step in TRACE_DATA if step['memory_delta'] > 0]
            deltas.sort(key=lambda x: x[1], reverse=True)
            hotspots = deltas[:5]
            
            # Calculate time hotspots (top 5 slowest lines)
            time_hotspots = {}
            for step in TRACE_DATA:
                line = step['line_no']
                t = step.get('exec_time_delta', 0)
                if line not in time_hotspots or t > time_hotspots[line]:
                    time_hotspots[line] = t
            time_hotspots_list = sorted(time_hotspots.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # Pass the data to the web app
            set_trace_data({
                'source': sourceLinesProcess(source_lines),
                'start_line': start_line,
                'trace': TRACE_DATA,
                'output': CAPTURED_OUTPUT,
                'hotspots': hotspots,
                'time_hotspots': time_hotspots_list,
                'total_exec_time': total_exec_time
            })
            
            print("Starting ChronoTrace Web UI...")
            # Open browser after a short delay to allow server to start
            threading.Timer(1.5, lambda: webbrowser.open("http://127.0.0.1:5000")).start()
            start_server(port=5000)
            
        return result
    return wrapper

def trace_code(code_string):
    """
    Traces execution of a code string.
    """
    global TRACE_DATA, CAPTURED_OUTPUT, CALL_STACK
    TRACE_DATA = []
    CAPTURED_OUTPUT = []
    CALL_STACK = []
    
    # Pre-process source lines
    source_lines = [line + '\n' for line in code_string.splitlines()]
    start_line = 1
    
    # Analyze AST for structure context
    ast_mapping = analyze_ast(code_string)
    
    # Start tracking memory and time
    tracemalloc.start()
    start_time = time.perf_counter_ns()  # Use nanoseconds for precision
    previous_memory = 0
    previous_time = start_time
    step_times = {}  # Track time per line
    
    def trace_func(frame, event, arg):
        nonlocal previous_memory, previous_time
        filename = frame.f_code.co_filename
        
        # Only trace the executed string
        if filename != "<string>":
            return None
        
        # Handle function call events
        if event == 'call':
            func_name = frame.f_code.co_name
            CALL_STACK.append({
                'name': func_name,
                'line': frame.f_lineno,
                'filename': filename
            })
            return trace_func
        
        # Handle function return events
        if event == 'return':
            if CALL_STACK:
                CALL_STACK.pop()
            return trace_func
            
        if event == 'line':
            timestamp = time.time()
            current_perf = time.perf_counter_ns()
            line_no = frame.f_lineno
            
            # Calculate time delta (ensure at least 1 nanosecond to avoid 0 values)
            exec_time_delta_ns = max(1, current_perf - previous_time)
            exec_time_delta = exec_time_delta_ns / 1_000_000_000.0  # Convert to seconds
            previous_time = current_perf
            
            locals_snapshot = {}
            for key, value in frame.f_locals.items():
                if key.startswith('__'): continue
                try:
                    locals_snapshot[key] = serialize(value)
                except Exception as e:
                    locals_snapshot[key] = f"<Error serialization: {str(e)}>"
            
            current, peak = tracemalloc.get_traced_memory()
            memory_delta = current - previous_memory
            previous_memory = current
            gc_counts = gc.get_count()
            
            # Get AST context
            stmt_info = ast_mapping.get(line_no, {})
            stmt_type = stmt_info.get('type', 'Unknown')
            stmt_source = stmt_info.get('source', '')
            
            # Track time per line for hotspots
            if line_no not in step_times:
                step_times[line_no] = 0
            step_times[line_no] += exec_time_delta_ns
            
            elapsed_ns = current_perf - start_time
            elapsed_seconds = elapsed_ns / 1_000_000_000.0
            
            # Debug: Print timing info for first few steps
            if len(TRACE_DATA) < 3:
                print(f"[TRACE] Line {line_no}: exec_time_delta={exec_time_delta}, elapsed={elapsed_seconds}")

            TRACE_DATA.append({
                'timestamp': timestamp,
                'line_no': line_no,
                'locals': locals_snapshot,
                'memory': current,
                'memory_delta': memory_delta,
                'peak_memory': peak,
                'gc_counts': gc_counts,
                'event': event,
                'filename': filename,
                'stmt_type': stmt_type,
                'stmt_source': stmt_source,
                'call_stack': list(CALL_STACK),
                'exec_time_delta': exec_time_delta,
                'elapsed_time': elapsed_seconds
            })
        return trace_func

    sys.settrace(trace_func)
    
    original_stdout = sys.stdout
    sys.stdout = StreamCapturer(original_stdout)
    
    try:
        exec(code_string, {'__name__': '__main__'})
    except Exception as e:
        print(f"Exception during execution: {e}")
        sys.stdout.write(f"\nError: {str(e)}")
    finally:
        end_time = time.perf_counter_ns()
        total_exec_time = (end_time - start_time) / 1_000_000_000.0
        
        sys.stdout = original_stdout
        sys.settrace(None)
        tracemalloc.stop()
        
        # Process memory hotspots
        deltas = [(step['line_no'], step['memory_delta']) for step in TRACE_DATA if step['memory_delta'] > 0]
        deltas.sort(key=lambda x: x[1], reverse=True)
        hotspots = deltas[:5]
        
        # Process time hotspots
        time_hotspots_list = sorted(step_times.items(), key=lambda x: x[1], reverse=True)[:5]
        time_hotspots_seconds = [(line, t / 1_000_000_000.0) for line, t in time_hotspots_list]
        
        return {
            'success': True,
            'steps': len(TRACE_DATA),
            'source': sourceLinesProcess(source_lines),
            'start_line': start_line,
            'trace': TRACE_DATA,
            'output': CAPTURED_OUTPUT,
            'hotspots': hotspots,
            'time_hotspots': time_hotspots_seconds,
            'total_exec_time': total_exec_time
        }

def sourceLinesProcess(lines):
    # Ensure lines are strings and handle encoding if necessary (usually fine in Python 3)
    return lines
