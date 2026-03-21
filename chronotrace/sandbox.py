"""
Code execution sandbox for ChronoTrace.
Provides restricted execution environment with resource limits.
"""
import sys
import io
import multiprocessing
from typing import Any, Callable, Dict, Optional


# Dangerous modules that allow system access
BLOCKED_MODULES = {
    'os', 'sys', 'subprocess', 'shutil',
    'socket', 'http', 'urllib', 'requests',
    'ctypes', 'multiprocessing', 'threading',
    'importlib', 'pkgutil',
    'shelve', 'pickle',
    'builtins', '_thread',  # Critical: prevent sandbox escape
}

# Modules allowed for teaching purposes
ALLOWED_MODULES = {
    'pathlib', 'inspect', 'collections', 'itertools',
    'math', 'json', 'csv', 're',
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
    'type',  # Block type() to prevent dynamic class creation
}


def create_restricted_globals() -> Dict[str, Any]:
    """Create a restricted global namespace for code execution."""
    import builtins

    safe_builtins = {}
    allowed_builtins = [
        'int', 'float', 'str', 'bool', 'list', 'dict', 'tuple', 'set',
        'frozenset', 'complex',
        'print', 'len', 'range', 'enumerate', 'zip', 'map', 'filter',
        'sorted', 'reversed', 'min', 'max', 'sum', 'abs', 'round',
        'pow', 'divmod', 'any', 'all',
        'isinstance', 'issubclass',
        'bin', 'hex', 'oct', 'chr', 'ord',
        'iter', 'next', 'slice',
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
    """Validate code for potentially dangerous patterns."""
    import ast

    try:
        tree = ast.parse(code_string)
    except SyntaxError as e:
        return f"Syntax error: {e}"

    dangerous_attrs = {
        '__subclasses__', '__bases__', '__mro__',
        '__globals__', '__code__', '__builtins__',
        '__import__', '__loader__', '__class__',
        '__getattribute__', '__setattr__', '__delattr__',
        '__init_subclass__', '__setitem__', '__getitem__',
        '__dict__', '__weakref__',
    }

    # Keys that must not be accessed via subscript on any object
    dangerous_subscript_keys = {
        'eval', 'exec', 'compile', '__import__',
        'open', 'input', 'breakpoint',
        'globals', 'locals', 'vars',
        'getattr', 'setattr', 'delattr',
    }

    # Dangerous attribute calls (e.g., time.sleep, os.system)
    dangerous_attr_calls = {
        'sleep', 'system', 'popen', 'spawn', 'execv', 'execve',
        'fork', 'kill', 'signal',
    }

    # Blocked base classes for inheritance (type is blocked, object is allowed)
    blocked_bases = {'type'}

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

        # Block dangerous function calls (direct)
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in BLOCKED_BUILTINS:
                    return f"Blocked function call: {node.func.id}"
                # Also block dangerous function names like sleep
                if node.func.id in dangerous_attr_calls:
                    return f"Blocked function call: {node.func.id}"

        # Block class definitions inheriting from blocked bases
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                if isinstance(base, ast.Name) and base.id in blocked_bases:
                    return f"Blocked inheritance from: {base.id}"

        # Block dangerous attribute access
        if isinstance(node, ast.Attribute):
            if node.attr in dangerous_attrs:
                return f"Blocked attribute access: {node.attr}"

        # Block subscript access to dangerous keys (e.g., __builtins__["eval"])
        if isinstance(node, ast.Subscript):
            # Check for string key access: obj["key"]
            if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
                key = node.slice.value
                # Block access to dangerous builtins via subscript
                if key in dangerous_subscript_keys or key in BLOCKED_BUILTINS:
                    return f"Blocked subscript access: {key}"
                # Block access to __builtins__ or dangerous attrs
                if key in dangerous_attrs:
                    return f"Blocked subscript access: {key}"
            # Also block __builtins__[variable] patterns
            if isinstance(node.value, ast.Name) and node.value.id == '__builtins__':
                return "Blocked access to __builtins__"

        # Block calls on subscript results (e.g., __builtins__["eval"](...))
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Subscript):
                if isinstance(node.func.slice, ast.Constant) and isinstance(node.func.slice.value, str):
                    key = node.func.slice.value
                    if key in dangerous_subscript_keys or key in BLOCKED_BUILTINS:
                        return f"Blocked function call via subscript: {key}"

        # Block dangerous attribute calls (e.g., time.sleep, os.system)
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if node.func.attr in dangerous_attr_calls:
                    return f"Blocked dangerous call: {node.func.attr}"

    return None


def _apply_resource_limits():
    """Apply OS resource limits. Unix only, no-op on Windows."""
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024))
        resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
        resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
    except (ImportError, ValueError, OSError):
        pass


def _run_in_subprocess(target_fn: Callable, args: tuple, timeout: int = 10) -> Dict[str, Any]:
    """
    Run a function in an isolated subprocess with timeout.

    Args:
        target_fn: Function to run (must be picklable)
        args: Arguments tuple for target_fn
        timeout: Timeout in seconds

    Returns:
        Dict from result_queue, or timeout/error dict
    """
    ctx = multiprocessing.get_context('spawn')
    result_queue = ctx.Queue()
    process = ctx.Process(target=target_fn, args=args + (result_queue,))

    process.start()
    process.join(timeout)

    timed_out = False
    if process.is_alive():
        timed_out = True
        process.kill()
        process.join()

    # Try to get result from queue (may have data even if killed)
    result = None
    try:
        if not result_queue.empty():
            result = result_queue.get_nowait()
    except Exception:
        pass

    if result is not None:
        # If we got a result but it was a timeout, mark it
        if timed_out and not result.get('timed_out'):
            result['timed_out'] = True
        return result

    if timed_out:
        return {
            'success': False,
            'error': f'Execution timed out after {timeout} seconds. Possible infinite loop.',
            'timed_out': True,
        }

    # Process ended without timeout but no result
    return {
        'success': False,
        'error': 'Process terminated unexpectedly. Code may have crashed.',
        'timed_out': False,
    }


def _exec_worker(code: str, result_queue):
    """Worker for execute_sandboxed."""
    try:
        error = validate_code_safety(code)
        if error:
            result_queue.put({
                'success': False, 'output': '', 'stderr': '',
                'error': error, 'timed_out': False,
            })
            return

        _apply_resource_limits()
        restricted_globals = create_restricted_globals()

        old_stdout, old_stderr = sys.stdout, sys.stderr
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
            sys.stdout, sys.stderr = old_stdout, old_stderr

        result_queue.put({
            'success': exec_error is None,
            'output': stdout_val,
            'stderr': stderr_val,
            'error': exec_error,
            'timed_out': False,
        })

    except Exception as e:
        result_queue.put({
            'success': False, 'output': '', 'stderr': '',
            'error': str(e), 'timed_out': False,
        })


def execute_sandboxed(code_string: str, timeout: int = 10) -> Dict[str, Any]:
    """Execute code in a sandboxed subprocess."""
    return _run_in_subprocess(_exec_worker, (code_string,), timeout)


def _trace_worker(code: str, steps: int, result_queue):
    """Worker for trace_code_sandboxed."""
    try:
        import os

        # Validate FIRST, then apply limits
        error = validate_code_safety(code)
        if error:
            result_queue.put({
                'success': False, 'had_error': True,
                'error': f'Security check failed: {error}',
                'steps': 0, 'trace': [], 'output': [], 'source': [],
                'hotspots': [], 'time_hotspots': [], 'total_exec_time': 0,
            })
            return

        _apply_resource_limits()

        sandbox_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.dirname(sandbox_dir)
        if project_dir not in sys.path:
            sys.path.insert(0, project_dir)

        from chronotrace.core import trace_code

        result = trace_code(code, max_steps=steps)
        result_queue.put(result.to_dict())

    except Exception as e:
        result_queue.put({
            'success': False, 'had_error': True,
            'error': str(e),
            'steps': 0, 'trace': [], 'output': [], 'source': [],
            'hotspots': [], 'time_hotspots': [], 'total_exec_time': 0,
        })


def trace_code_sandboxed(code_string: str, max_steps: int = 50000, timeout: int = 30) -> Dict[str, Any]:
    """Execute trace_code in a sandboxed subprocess."""
    result = _run_in_subprocess(_trace_worker, (code_string, max_steps), timeout)

    # Ensure consistent return format for timeout/errors
    if 'trace' not in result:
        result.setdefault('success', False)
        result.setdefault('had_error', False)
        result.setdefault('steps', 0)
        result.setdefault('trace', [])

    return result


# Backward compatibility
execute_in_subprocess = execute_sandboxed
