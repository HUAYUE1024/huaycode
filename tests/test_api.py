"""
ChronoTrace API Integration Tests
"""
import unittest
import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chronotrace.web.app import app, store


class TestAPIRoutes(unittest.TestCase):
    """Test Flask API routes"""

    def setUp(self):
        """Set up test client"""
        app.config['TESTING'] = True
        self.client = app.test_client()
        # Clear store before each test
        store._history = []
        store._trace_data = None

    def test_index_route(self):
        """Test index page loads"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_status_endpoint(self):
        """Test /api/v1/status returns correct data"""
        response = self.client.get('/api/v1/status')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertEqual(data['status'], 'online')
        self.assertEqual(data['version'], 'v1')
        self.assertIn('python_version', data)
        self.assertIn('branch', data)
        self.assertIn('env', data)
        # Should use real platform info
        self.assertNotEqual(data['python_version'], '3.12.0')  # Not hardcoded

    def test_trace_endpoint_empty(self):
        """Test /api/v1/trace with no data"""
        response = self.client.get('/api/v1/trace')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertEqual(data, {})

    def test_run_endpoint_valid_code(self):
        """Test /api/v1/run with valid code"""
        response = self.client.post(
            '/api/v1/run',
            json={'code': 'x = 1\ny = 2\nz = x + y'},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertGreater(data['steps'], 0)

    def test_run_endpoint_empty_code(self):
        """Test /api/v1/run with empty code"""
        response = self.client.post(
            '/api/v1/run',
            json={'code': ''},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    def test_run_endpoint_no_code(self):
        """Test /api/v1/run without code field"""
        response = self.client.post(
            '/api/v1/run',
            json={},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    def test_run_endpoint_blocked_import(self):
        """Test /api/v1/run blocks dangerous imports"""
        response = self.client.post(
            '/api/v1/run',
            json={'code': 'import os\nos.system("ls")'},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 403)

        data = json.loads(response.data)
        self.assertIn('Security check failed', data['error'])

    def test_run_endpoint_blocked_subprocess(self):
        """Test /api/v1/run blocks subprocess"""
        response = self.client.post(
            '/api/v1/run',
            json={'code': 'import subprocess\nsubprocess.run(["ls"])'},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 403)

    def test_history_endpoint(self):
        """Test /api/v1/history"""
        # Run some code first
        self.client.post(
            '/api/v1/run',
            json={'code': 'x = 1'},
            content_type='application/json'
        )

        response = self.client.get('/api/v1/history')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)
        self.assertIn('id', data[0])
        self.assertIn('steps', data[0])

    def test_history_entry_endpoint(self):
        """Test /api/v1/history/<id>"""
        # Run code to create history
        self.client.post(
            '/api/v1/run',
            json={'code': 'x = 1'},
            content_type='application/json'
        )

        response = self.client.get('/api/v1/history/1')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertIn('trace', data)

    def test_history_entry_not_found(self):
        """Test /api/v1/history/<id> with invalid id"""
        response = self.client.get('/api/v1/history/999')
        self.assertEqual(response.status_code, 404)

    def test_legacy_api_compatibility(self):
        """Test legacy /api endpoints still work"""
        response = self.client.get('/api/trace')
        self.assertEqual(response.status_code, 200)

        response = self.client.get('/api/history')
        self.assertEqual(response.status_code, 200)

    def test_compare_endpoint(self):
        """Test /api/v1/compare"""
        # Create two executions
        self.client.post(
            '/api/v1/run',
            json={'code': 'x = 1'},
            content_type='application/json'
        )
        self.client.post(
            '/api/v1/run',
            json={'code': 'x = 2'},
            content_type='application/json'
        )

        response = self.client.post(
            '/api/v1/compare',
            json={'id_a': 1, 'id_b': 2},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertIn('execution_a', data)
        self.assertIn('execution_b', data)
        self.assertIn('diff', data)

    def test_security_headers(self):
        """Test security headers are present"""
        response = self.client.get('/')
        self.assertEqual(response.headers.get('X-Content-Type-Options'), 'nosniff')
        self.assertEqual(response.headers.get('X-Frame-Options'), 'SAMEORIGIN')


class TestSandboxSecurity(unittest.TestCase):
    """Test sandbox security features"""

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_block_os_import(self):
        """Block os module import"""
        response = self.client.post(
            '/api/v1/run',
            json={'code': 'import os'},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 403)

    def test_block_sys_import(self):
        """Block sys module import"""
        response = self.client.post(
            '/api/v1/run',
            json={'code': 'import sys'},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 403)

    def test_block_file_open(self):
        """Block file operations via attribute access check"""
        code = """
f = open('/etc/passwd', 'r')
content = f.read()
"""
        response = self.client.post(
            '/api/v1/run',
            json={'code': code},
            content_type='application/json'
        )
        # Should be blocked
        self.assertIn(response.status_code, [403, 500])

    def test_block_eval(self):
        """Block eval calls"""
        response = self.client.post(
            '/api/v1/run',
            json={'code': 'eval("1+1")'},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 403)

    def test_block_exec(self):
        """Block exec calls"""
        response = self.client.post(
            '/api/v1/run',
            json={'code': 'exec("x=1")'},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 403)

    def test_block_dunder_import(self):
        """Block __import__"""
        response = self.client.post(
            '/api/v1/run',
            json={'code': '__import__("os")'},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 403)

    def test_allow_safe_math(self):
        """Allow safe math operations"""
        response = self.client.post(
            '/api/v1/run',
            json={'code': 'x = 1 + 2 * 3'},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)

    def test_allow_safe_loops(self):
        """Allow safe loops"""
        response = self.client.post(
            '/api/v1/run',
            json={'code': 'for i in range(10):\n    x = i * 2'},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)

    def test_allow_safe_functions(self):
        """Allow safe function definitions"""
        code = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

result = factorial(5)
"""
        response = self.client.post(
            '/api/v1/run',
            json={'code': code},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)

    def test_allow_pathlib(self):
        """Allow pathlib for teaching purposes"""
        code = """
from pathlib import Path
p = Path('.')
"""
        response = self.client.post(
            '/api/v1/run',
            json={'code': code},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)

    def test_allow_math(self):
        """Allow math module"""
        code = """
import math
x = math.sqrt(16)
y = math.pi
"""
        response = self.client.post(
            '/api/v1/run',
            json={'code': code},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)

    def test_allow_json(self):
        """Allow json module"""
        code = """
import json
data = json.loads('{"a": 1}')
"""
        response = self.client.post(
            '/api/v1/run',
            json={'code': code},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)

    def test_allow_collections(self):
        """Allow collections module"""
        code = """
from collections import Counter, defaultdict
c = Counter([1, 2, 2, 3])
"""
        response = self.client.post(
            '/api/v1/run',
            json={'code': code},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)


class TestTraceErrorHandling(unittest.TestCase):
    """Test trace error handling returns correct success/had_error"""

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_normal_code_success_true_had_error_false(self):
        """Normal code: success=True, had_error=False"""
        response = self.client.post(
            '/api/v1/run',
            json={'code': 'x = 1 + 2'},
            content_type='application/json'
        )
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertFalse(data['had_error'])
        self.assertIsNone(data.get('error'))

    def test_error_code_success_true_had_error_true(self):
        """Error code: success=True (trace worked), had_error=True"""
        response = self.client.post(
            '/api/v1/run',
            json={'code': 'x = 1 / 0'},
            content_type='application/json'
        )
        data = json.loads(response.data)
        self.assertTrue(data['success'])      # Trace completed
        self.assertTrue(data['had_error'])     # User code had error
        self.assertIsNotNone(data.get('error'))
        self.assertIn('division', data['error'].lower())


if __name__ == '__main__':
    unittest.main(verbosity=2)
