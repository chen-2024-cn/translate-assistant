"""Qt路径配置回归: mock环境/路径选择,不改系统Qt环境或启动窗口。"""
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from qt_runtime import find_windows_plugins, configure_qt_runtime


class TestQtRuntime(unittest.TestCase):
    def test_package_plugins_found(self):
        root = Path('artifacts/test-temp')
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as temp:
            package = Path(temp)
            file = package / 'Qt5/plugins/platforms/qwindows.dll'
            file.parent.mkdir(parents=True)
            file.touch()
            self.assertEqual(find_windows_plugins(package), package.resolve() / 'Qt5/plugins')

    def test_missing_plugin_reported_not_silent(self):
        with mock.patch('qt_runtime.Path.is_file', return_value=False):
            with self.assertRaisesRegex(RuntimeError, 'qwindows.dll'):
                find_windows_plugins(Path('missing-pyqt'))

    def test_external_qt_folder_not_used(self):
        with mock.patch('qt_runtime.Path.is_file', return_value=False):
            with self.assertRaises(RuntimeError):
                find_windows_plugins(Path('package'), str(Path('other-qt').resolve()))

    def test_process_environment_configured_and_offscreen_preserved(self):
        from PyQt5.QtCore import QCoreApplication
        plugins = Path('local-pyqt/Qt5/plugins').resolve()
        with mock.patch('qt_runtime.sys.platform', 'win32'), \
                mock.patch('qt_runtime.find_windows_plugins', return_value=plugins), \
                mock.patch.dict(os.environ, {'QT_PLUGIN_PATH': 'wrong-qt', 'QT_QPA_PLATFORM': 'offscreen'}), \
                mock.patch.object(QCoreApplication, 'setLibraryPaths') as paths:
            self.assertEqual(configure_qt_runtime(), plugins)
            self.assertNotIn('QT_PLUGIN_PATH', os.environ)
            self.assertEqual(os.environ['QT_QPA_PLATFORM'], 'offscreen')
            self.assertEqual(os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'], str(plugins / 'platforms'))
            paths.assert_called_once_with([str(plugins)])

    def test_frozen_keeps_pyinstaller_environment(self):
        with mock.patch('qt_runtime.sys.frozen', True, create=True), \
                mock.patch.dict(os.environ, {'QT_PLUGIN_PATH': 'bundled-qt'}):
            self.assertIsNone(configure_qt_runtime())
            self.assertEqual(os.environ['QT_PLUGIN_PATH'], 'bundled-qt')

    def test_nonwindows_not_modified(self):
        with mock.patch('qt_runtime.sys.platform', 'linux'), \
                mock.patch.dict(os.environ, {'QT_PLUGIN_PATH': 'ci-qt'}):
            self.assertIsNone(configure_qt_runtime())
            self.assertEqual(os.environ['QT_PLUGIN_PATH'], 'ci-qt')
