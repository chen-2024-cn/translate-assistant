"""解释器范围测试,不切换用户Python环境。"""
import unittest
from unittest import mock

from python_runtime import check_python_runtime


class TestPythonRuntime(unittest.TestCase):
    def setUp(self):
        patches = [
            mock.patch('python_runtime.sys.platform', 'win32'),
            mock.patch('python_runtime.platform.machine', return_value='AMD64'),
            mock.patch('python_runtime.struct.calcsize', return_value=8),
            mock.patch('python_runtime.sysconfig.get_config_var', return_value=None),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def test_supported_standard_versions(self):
        for minor in range(11, 16):
            with self.subTest(minor=minor), mock.patch('python_runtime.sys.version_info', (3, minor, 0)):
                check_python_runtime()

    def test_unsupported_version_reports_current_interpreter(self):
        for version in ((3, 10, 0), (3, 16, 0)):
            with self.subTest(version=version), mock.patch('python_runtime.sys.version_info', version):
                with self.assertRaisesRegex(RuntimeError, '3.11-3.15'):
                    check_python_runtime()

    def test_nonwindows_rejected(self):
        with mock.patch('python_runtime.sys.platform', 'linux'):
            with self.assertRaises(RuntimeError):
                check_python_runtime()

    def test_32bit_rejected(self):
        with mock.patch('python_runtime.struct.calcsize', return_value=4):
            with self.assertRaises(RuntimeError):
                check_python_runtime()

    def test_arm_rejected(self):
        with mock.patch('python_runtime.platform.machine', return_value='ARM64'):
            with self.assertRaises(RuntimeError):
                check_python_runtime()

    def test_free_threaded_rejected(self):
        with mock.patch('python_runtime.sysconfig.get_config_var', return_value=1):
            with self.assertRaises(RuntimeError):
                check_python_runtime()

    def test_frozen_does_not_depend_on_host_python(self):
        with mock.patch('python_runtime.sys.frozen', True, create=True), \
                mock.patch('python_runtime.sys.platform', 'linux'):
            check_python_runtime()
