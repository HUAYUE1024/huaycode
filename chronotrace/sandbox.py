"""
Code execution sandbox for ChronoTrace.
Provides restricted execution environment with resource limits.
"""
import sys
import io
import multiprocessing
from typing import Any, Dict, Optional, Tuple


# Dangerous modules that allow system access
BLOCKED_MODULES = {
    'os', 'sys', 'subprocess', 'shutil',
    'socket', 'http', 'urllib', 'requests',
    'ctypes', 'multiprocessing', 'threading',
    'importlib', 'pkgutil',
    'shelve', 'pickle',
}

# Modules allowed for teaching purposes
ALLOWED_MODULES = {
    'pathlib', 'inspect', 'collections', 'itertools',
    'math', 'random', 'json', 'csv', 're',
    'functools', 'operator', 'string', 'textwrap',
    'datetime', 'time', 'calendar',
    'copy', 'pprint', 'enum', 'dataclasses',
    'typing', 'abc', 'contextlib',
}

# Dangerous builtins to block
BLOCKED_BUILTINS = {
    'exec', 'eval', 'compile', '__import__',
    'open', 'input', 'breakpoint',
    'exit', 'quit',
    'globals', 'locals', 'vars',
    'getattr', 'setattr', 'delattr',
    'dir', 'id', 'hash', 'callable',
}


def create_restricted_globals() -> Dict[str, Any]:
    """Create a restricted global namespace for code execution."""
    import builtins

    # Build safe builtins
    safe_builtins = {}
    allowed_builtins = [
        # Types
        'int', 'float', 'str', 'bool', 'list', 'dict', 'tuple', 'set',
        'frozenset', 'bytes', 'bytearray', 'complex',
        # Functions
        'print', 'len', 'range', 'enumerate', 'zip', 'map', 'filter',
        'sorted', 'reversed', 'min', 'max', 'sum', 'abs', 'round',
        'pow', 'divmod', 'any', 'all',
        # Type checking
        'isinstance', 'issubclass', 'type',
        # Math
        'bin', 'hex', 'oct', 'chr', 'ord',
        # Iteration
        'iter', 'next', 'slice',
        # Other
        'repr', 'ascii', 'format',
        'True', 'False', 'None',
        'NotImplemented', 'Ellipsis',
        'Exception', 'ValueError', 'TypeError', 'KeyError',
        'IndexError', 'AttributeError', 'RuntimeError',
        'ZeroDivisionError', 'StopIteration',
    ]

    for name in allowed_builtins:
        if hasattr(builtins, name):
            safe_builtins[name] = getattr(builtins, name)

    return {
        '__builtins__': safe_builtins,
        '__name__': '__main__',
    }


def validate_code_safety(code_string: str) -> Optional[str]:
    """
    Validate code for potentially dangerous patterns.
    Returns error message if unsafe, None if safe.
    """
    import ast

    try:
        tree = ast.parse(code_string)
    except SyntaxError as e:
        return f"Syntax error: {e}"

    dangerous_attrs = {
        '__subclasses__', '__bases__',
        '__globals__', '__code__', '__builtins__',
        '__import__', '__loader__',
    }

    dangerous_subscript_keys = {
        '__builtins__', '__globals__', '__import__',
    }

    for node in ast.walk(tree):
        # Block dangerous imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = alias.name.split('.')[0]
                if module in BLOCKED_MODULES:
                    return f"Blocked import: {alias.name}"

        if isinstance(node, ast.ImportFrom):
            if node.module:
                module = node.module.split('.')[0]
                if module in BLOCKED_MODULES:
                    return f"Blocked import from: {node.module}"

        # Block dangerous function calls by name
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in BLOCKED_BUILTINS:
                    return f"Blocked function call: {node.func.id}"

            # Block calls via attribute: obj.dangerous()
            if isinstance(node.func, ast.Attribute):
                if node.func.attr in BLOCKED_BUILTINS:
                    return f"Blocked function call: {node.func.attr}"

        # Block attribute access to dangerous dunder methods
        if isinstance(node, ast.Attribute):
            if node.attr in dangerous_attrs:
                return f"Blocked attribute access: {node.attr}"

        # Block __builtins__ and other dangerous keys via subscript: obj['__builtins__']
        if isinstance(node, ast.Subscript):
            if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
                if node.slice.value in dangerous_subscript_keys:
                    return f"Blocked subscript access: {node.slice.value}"

        # Block type() with dynamic bases that could escape sandbox
        # type('X', (object,), {'__builtins__': ...})
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == 'type':
                if len(node.args) == 3:
                    if isinstance(node.args[2], ast.Dict):
                        for key_node in node.args[2].keys:
                            if isinstance(key_node, ast.Constant) and isinstance(key_node.value, str):
                                if key_node.value in dangerous_subscript_keys:
                                    return f"Blocked type() with dangerous key: {key_node.value}"

        # Block chr() calls that could reconstruct blocked names
        # chr(...)[chr(...)] patterns - already covered by ast.Call check above for chr
        # but we also need to block attribute access patterns like:
        # getattr(obj, chr(...)) - covered by getattr being in BLOCKED_BUILTINS

    return None


def _apply_resource_limits():
    """Apply OS resource limits to the current process. Unix only."""
    try:
        import resource
        # Limit virtual memory to 256MB
        resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024))
        # Limit number of open file descriptors
        resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
        # Limit CPU time to 30 seconds
        resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
    except (ImportError, ValueError, OSError):
        # resource module not available (Windows) or limit already lower
        pass


def execute_sandboxed(code_string: str, timeout: int = 10) -> Dict[str, Any]:
    """
    Execute code in a sandboxed subprocess with timeout.

    Returns:
        dict with keys:
            - success: bool (True if no exception occurred)
            - output: str (stdout)
            - stderr: str (stderr)
            - error: str or None (exception message if any)
            - timed_out: bool
    """
    def worker(code: str, result_queue):
        try:
            # Validate code safety (defense in depth)
            error = validate_code_safety(code)
            if error:
                result_queue.put({
                    'success': False,
                    'output': '',
                    'stderr': '',
                    'error': error,
                    'timed_out': False,
                })
                return

            # Create restricted environment
            restricted_globals = create_restricted_globals()

            # Apply resource limits
            _apply_resource_limits()

            # Capture output
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = io.StringIO()
            sys.stderr = io.StringIO()

            exec_error = None
            try:
                exec(compile(code, '<string>', 'exec'), restricted_globals)
            except Exception as e:
                exec_error = str(e)
            finally:
                stdout_val = sys.stdout.getvalue()
                stderr_val = sys.stderr.getvalue()
                sys.stdout = old_stdout
                sys.stderr = old_stderr

            result_queue.put({
                'success': exec_error is None,
                'output': stdout_val,
                'stderr': stderr_val,
                'error': exec_error,
                'timed_out': False,
            })

        except Exception as e:
            result_queue.put({
                'success': False,
                'output': '',
                'stderr': '',
                'error': str(e),
                'timed_out': False,
            })

    # Run in subprocess for isolation
    ctx = multiprocessing.get_context('spawn')
    result_queue = ctx.Queue()
    process = ctx.Process(target=worker, args=(code_string, result_queue))

    process.start()
    process.join(timeout)

    if process.is_alive():
        process.kill()
        process.join()
        return {
            'success': False,
            'output': '',
            'stderr': '',
            'error': f"Execution timed out after {timeout} seconds",
            'timed_out': True,
        }

    if result_queue.empty():
        return {
            'success': False,
            'output': '',
            'stderr': '',
            'error': "Process terminated unexpectedly",
            'timed_out': False,
        }

    return result_queue.get_nowait()


# Backward compatibility alias
def execute_in_subprocess(code_string: str, timeout: int = 10) -> Dict[str, Any]:
    """Deprecated: use execute_sandboxed instead."""
    return execute_sandboxed(code_string, timeout)


def _trace_worker(code: str, steps: int, result_queue):
    """Worker function for trace_code_sandboxed - must be module-level for pickling."""
    try:
        import os

        # Apply resource limits first
        _apply_resource_limits()

        # Validate code safety (defense in depth - subprocess level)
        error = validate_code_safety(code)
        if error:
            result_queue.put({
                'success': False,
                'had_error': True,
                'error': f'Security check failed: {error}',
                'steps': 0,
                'trace': [],
                'output': [],
                'source': [],
                'hotspots': [],
                'time_hotspots': [],
                'total_exec_time': 0,
            })
            return

        # Add project to path
        sandbox_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.dirname(sandbox_dir)
        if project_dir not in sys.path:
            sys.path.insert(0, project_dir)

        from chronotrace.core import trace_code

        result = trace_code(code, max_steps=steps)
        result_queue.put(result.to_dict())

    except Exception as e:
        result_queue.put({
            'success': False,
            'had_error': True,
            'error': str(e),
            'steps': 0,
            'trace': [],
            'output': [],
            'source': [],
            'hotspots': [],
            'time_hotspots': [],
            'total_exec_time': 0,
        })


def trace_code_sandboxed(code_string: str, max_steps: int = 50000, timeout: int = 30) -> Dict[str, Any]:
    """
    Execute trace_code in a sandboxed subprocess.

    This isolates sys.settrace and sys.stdout changes from the main process,
    preventing global state pollution in multi-threaded web servers.

    Args:
        code_string: Python code to trace
        max_steps: Maximum trace steps
        timeout: Execution timeout in seconds

    Returns:
        TraceResult dict with success/had_error fields
    """
    ctx = multiprocessing.get_context('spawn')
    result_queue = ctx.Queue()
    process = ctx.Process(target=_trace_worker, args=(code_string, max_steps, result_queue))

    process.start()
    process.join(timeout)

    if process.is_alive():
        process.kill()
        process.join()
        return {
            'success': False,
            'had_error': False,
            'error': f'Execution timed out after {timeout} seconds',
            'timed_out': True,
            'steps': 0,
            'trace': [],
        }

    if result_queue.empty():
        return {
            'success': False,
            'had_error': False,
            'error': 'Process terminated unexpectedly',
            'steps': 0,
            'trace': [],
        }

    return result_queue.get_nowait()
