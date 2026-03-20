"""
Code execution sandbox for ChronoTrace.
Provides restricted execution environment with resource limits.
"""
import sys
import io
import signal
import multiprocessing
from functools import wraps
from typing import Any, Dict, Optional


# Dangerous builtins to remove
BLOCKED_BUILTINS = [
    'exec', 'eval', 'compile', '__import__',
    'open', 'input', 'breakpoint',
    'exit', 'quit',
    'globals', 'locals', 'vars',
    'getattr', 'setattr', 'delattr',
    'dir', 'id', 'hash', 'callable',
]

# Dangerous modules to block
BLOCKED_MODULES = [
    'os', 'sys', 'subprocess', 'shutil',
    'socket', 'http', 'urllib', 'requests',
    'ctypes', 'multiprocessing', 'threading',
    'importlib', 'pkgutil', 'inspect',
    'pathlib', 'shelve', 'pickle', 'shelve',
]


def create_restricted_globals() -> Dict[str, Any]:
    """Create a restricted global namespace for code execution."""
    import builtins

    # Create safe builtins dict
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
        'repr', 'ascii', 'format', 'help',
        'True', 'False', 'None',
        'NotImplemented', 'Ellipsis',
        'Exception', 'ValueError', 'TypeError', 'KeyError',
        'IndexError', 'AttributeError', 'RuntimeError',
        'ZeroDivisionError', 'StopIteration',
    ]

    for name in allowed_builtins:
        if hasattr(builtins, name):
            safe_builtins[name] = getattr(builtins, name)

    # Create restricted globals
    restricted_globals = {
        '__builtins__': safe_builtins,
        '__name__': '__main__',
    }

    return restricted_globals


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

    for node in ast.walk(tree):
        # Block dangerous imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split('.')[0] in BLOCKED_MODULES:
                    return f"Blocked import: {alias.name}"

        if isinstance(node, ast.ImportFrom):
            if node.module and node.module.split('.')[0] in BLOCKED_MODULES:
                return f"Blocked import from: {node.module}"

        # Block dangerous function calls
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                blocked_funcs = (
                    'exec', 'eval', 'compile', '__import__',
                    'open', 'input', 'breakpoint',
                    'exit', 'quit', 'getattr', 'setattr', 'delattr',
                )
                if node.func.id in blocked_funcs:
                    return f"Blocked function call: {node.func.id}"

        # Block attribute access to dangerous names
        if isinstance(node, ast.Attribute):
            dangerous_attrs = [
                '__subclasses__', '__class__', '__bases__',
                '__globals__', '__code__', '__builtins__',
                '__import__', '__loader__',
            ]
            if node.attr in dangerous_attrs:
                return f"Blocked attribute access: {node.attr}"

    return None


def execute_in_subprocess(code_string: str, timeout: int = 10) -> Dict[str, Any]:
    """
    Execute code in a separate process with timeout.
    Returns result dict with 'success', 'result', 'error', 'timed_out' keys.
    """
    result = {'success': False, 'result': None, 'error': None, 'timed_out': False}

    def worker(code: str, result_queue):
        try:
            # Validate code first
            error = validate_code_safety(code)
            if error:
                result_queue.put({'success': False, 'error': error, 'result': None})
                return

            # Create restricted environment
            restricted_globals = create_restricted_globals()

            # Capture output
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = io.StringIO()
            sys.stderr = io.StringIO()

            try:
                exec(compile(code, '<string>', 'exec'), restricted_globals)
                output = sys.stdout.getvalue()
                error_output = sys.stderr.getvalue()

                result_queue.put({
                    'success': True,
                    'result': {
                        'output': output,
                        'stderr': error_output,
                        'globals': {
                            k: v for k, v in restricted_globals.items()
                            if not k.startswith('_')
                        }
                    },
                    'error': None
                })
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr

        except Exception as e:
            result_queue.put({'success': False, 'error': str(e), 'result': None})

    # Use multiprocessing for true isolation
    ctx = multiprocessing.get_context('spawn')
    result_queue = ctx.Queue()
    process = ctx.Process(target=worker, args=(code_string, result_queue))

    process.start()
    process.join(timeout)

    if process.is_alive():
        process.kill()
        process.join()
        result['timed_out'] = True
        result['error'] = f"Execution timed out after {timeout} seconds"
    elif result_queue.empty():
        result['error'] = "Process terminated without result"
    else:
        result = result_queue.get_nowait()

    return result


class TimeoutError(Exception):
    pass


def timeout_handler(signum, frame):
    raise TimeoutError("Code execution timed out")


def execute_with_timeout(code_string: str, timeout: int = 10) -> Dict[str, Any]:
    """
    Execute code with timeout (Unix only, falls back to subprocess on Windows).
    """
    import platform

    if platform.system() == 'Windows':
        return execute_in_subprocess(code_string, timeout)

    # Unix: use signal-based timeout
    result = {'success': False, 'result': None, 'error': None, 'timed_out': False}

    # Validate code first
    error = validate_code_safety(code_string)
    if error:
        result['error'] = error
        return result

    # Set up timeout
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout)

    try:
        restricted_globals = create_restricted_globals()

        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()

        try:
            exec(compile(code_string, '<string>', 'exec'), restricted_globals)
            output = sys.stdout.getvalue()
            error_output = sys.stderr.getvalue()

            result['success'] = True
            result['result'] = {
                'output': output,
                'stderr': error_output,
            }
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)

    except TimeoutError:
        result['timed_out'] = True
        result['error'] = f"Execution timed out after {timeout} seconds"
    except Exception as e:
        result['error'] = str(e)

    return result
