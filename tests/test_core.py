"""
ChronoTrace Unit Tests
"""
import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chronotrace.core import serialize, analyze_ast, trace_code, TraceResult, TraceContext


class TestSerialize(unittest.TestCase):
    """Test serialization function"""

    def test_primitive_types(self):
        """Test primitive type serialization"""
        self.assertEqual(serialize(42), 42)
        self.assertEqual(serialize(3.14), 3.14)
        self.assertEqual(serialize("hello"), "hello")
        self.assertEqual(serialize(True), True)
        self.assertEqual(serialize(None), None)

    def test_list_serialization(self):
        """Test list serialization"""
        self.assertEqual(serialize([1, 2, 3]), [1, 2, 3])
        self.assertEqual(serialize([]), [])

    def test_nested_list(self):
        """Test nested list serialization"""
        data = [[1, 2], [3, 4]]
        self.assertEqual(serialize(data), [[1, 2], [3, 4]])

    def test_large_list_truncation(self):
        """Test large list gets truncated"""
        large_list = list(range(200))
        result = serialize(large_list)
        self.assertEqual(len(result), 101)  # 100 items + truncation marker
        self.assertEqual(result[-1], "<Truncated...>")

    def test_dict_serialization(self):
        """Test dictionary serialization"""
        data = {"a": 1, "b": 2}
        self.assertEqual(serialize(data), {"a": 1, "b": 2})

    def test_empty_dict(self):
        """Test empty dict serialization"""
        self.assertEqual(serialize({}), {})

    def test_max_depth(self):
        """Test max depth truncation"""
        deep = {"a": {"b": {"c": {"d": 1}}}}
        result = serialize(deep, max_depth=2)
        self.assertEqual(result["a"]["b"]["c"], "<Max Depth Reached>")


class TestAnalyzeAST(unittest.TestCase):
    """Test AST analysis function"""

    def test_simple_assignment(self):
        """Test simple assignment analysis"""
        code = "x = 1"
        result = analyze_ast(code)
        self.assertIn(1, result)
        self.assertEqual(result[1]['type'], 'Assign')

    def test_for_loop(self):
        """Test for loop analysis"""
        code = """
for i in range(10):
    x = i
"""
        result = analyze_ast(code)
        for_types = [v['type'] for v in result.values()]
        self.assertIn('For', for_types)

    def test_function_def(self):
        """Test function definition analysis"""
        code = """
def foo():
    return 1
"""
        result = analyze_ast(code)
        func_types = [v['type'] for v in result.values()]
        self.assertIn('FunctionDef', func_types)

    def test_invalid_syntax(self):
        """Test invalid syntax returns empty dict"""
        code = "def foo(:"
        result = analyze_ast(code)
        self.assertEqual(result, {})


class TestTraceContext(unittest.TestCase):
    """Test TraceContext thread-safe storage"""

    def test_clear(self):
        """Test clearing context"""
        ctx = TraceContext()
        ctx.add_trace_step({'line': 1})
        ctx.clear()
        self.assertEqual(len(ctx.trace_data), 0)

    def test_thread_safety(self):
        """Test basic thread safety"""
        import threading
        ctx = TraceContext()
        errors = []

        def add_steps():
            try:
                for i in range(100):
                    ctx.add_trace_step({'line': i})
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=add_steps) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)
        self.assertEqual(len(ctx.trace_data), 400)


class TestTraceCode(unittest.TestCase):
    """Test code tracing function"""

    def test_simple_trace(self):
        """Test simple code execution trace"""
        code = "x = 1\ny = 2\nz = x + y"
        result = trace_code(code)

        self.assertIsInstance(result, TraceResult)
        self.assertTrue(result.success)
        self.assertGreater(result.steps, 0)
        self.assertIsInstance(result.trace, list)

    def test_trace_result_to_dict(self):
        """Test TraceResult serialization"""
        code = "x = 1"
        result = trace_code(code)
        result_dict = result.to_dict()

        self.assertIn('success', result_dict)
        self.assertIn('steps', result_dict)
        self.assertIn('trace', result_dict)
        self.assertIn('total_exec_time', result_dict)

    def test_loop_trace(self):
        """Test loop execution trace"""
        code = """
for i in range(3):
    x = i * 2
"""
        result = trace_code(code)

        self.assertTrue(result.success)
        self.assertGreater(result.steps, 3)

    def test_function_trace(self):
        """Test function execution trace"""
        code = """
def add(a, b):
    return a + b

result = add(1, 2)
"""
        result = trace_code(code)

        self.assertTrue(result.success)
        self.assertGreater(result.steps, 0)

    def test_error_handling(self):
        """Test error handling in traced code"""
        code = """
x = 1
y = 0
z = x / y
"""
        result = trace_code(code)

        # Should capture the error but still return trace
        self.assertTrue(result.success)
        error_outputs = [o for o in result.output if 'Error' in str(o.get('content', ''))]
        self.assertGreater(len(error_outputs), 0)

    def test_memory_tracking(self):
        """Test memory tracking"""
        code = """
data = []
for i in range(100):
    data.append(i)
"""
        result = trace_code(code)

        self.assertTrue(result.success)
        memories = [step['memory'] for step in result.trace]
        self.assertGreater(max(memories), min(memories))

    def test_time_tracking(self):
        """Test time tracking"""
        code = """
import time
x = 1
time.sleep(0.01)
y = 2
"""
        result = trace_code(code)

        self.assertTrue(result.success)
        self.assertGreater(result.total_exec_time, 0)

        # Check individual step timing
        for step in result.trace:
            self.assertIn('elapsed_time', step)
            self.assertIn('exec_time_delta', step)

    def test_call_stack_tracking(self):
        """Test call stack tracking"""
        code = """
def foo():
    return 1

def bar():
    return foo()

x = bar()
"""
        result = trace_code(code)

        self.assertTrue(result.success)
        has_stack = any(
            len(step.get('call_stack', [])) > 0
            for step in result.trace
        )
        self.assertTrue(has_stack)

    def test_max_steps_limit(self):
        """Test max steps limiting"""
        code = """
for i in range(1000):
    x = i
"""
        result = trace_code(code, max_steps=50)

        self.assertTrue(result.success)
        self.assertLessEqual(result.steps, 50)

    def test_hotspots(self):
        """Test memory and time hotspots calculation"""
        code = """
data = []
for i in range(10):
    data.append(i * i)
"""
        result = trace_code(code)

        self.assertIsInstance(result.hotspots, list)
        self.assertIsInstance(result.time_hotspots, list)


if __name__ == '__main__':
    unittest.main(verbosity=2)
