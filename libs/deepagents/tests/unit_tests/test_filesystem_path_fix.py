"""测试 Windows Git Bash 环境下的路径修复功能."""

import os
import pytest
from unittest.mock import patch

from deepagents.middleware.filesystem import _validate_path


class TestWindowsPathFix:
    """测试 Windows 路径修复功能."""

    def test_unix_relative_paths(self):
        """测试 Unix 相对路径."""
        assert _validate_path("foo/bar") == "/foo/bar"
        assert _validate_path("./README.md") == "/README.md"  # normpath 会移除 ./
        assert _validate_path("test.py") == "/test.py"

    def test_unix_absolute_paths(self):
        """测试 Unix 绝对路径."""
        assert _validate_path("/home/user/file.txt") == "/home/user/file.txt"
        assert _validate_path("/tmp/test") == "/tmp/test"
        assert _validate_path("/./foo//bar") == "/foo/bar"

    def test_windows_absolute_paths_on_windows(self):
        """测试在 Windows 环境下的 Windows 绝对路径."""
        with patch('os.name', 'nt'):
            # 测试反斜杠路径
            assert _validate_path("F:\\Projects\\deepagents\\README.md") == "F:/Projects/deepagents/README.md"
            assert _validate_path("C:\\Users\\Admin\\file.txt") == "C:/Users/Admin/file.txt"
            
            # 测试正斜杠路径
            assert _validate_path("F:/Projects/deepagents/README.md") == "F:/Projects/deepagents/README.md"
            assert _validate_path("C:/Users/Admin/file.txt") == "C:/Users/Admin/file.txt"
            
            # 测试混合分隔符
            assert _validate_path("F:\\Projects/deepagents/README.md") == "F:/Projects/deepagents/README.md"

    def test_windows_absolute_paths_on_unix(self):
        """测试在 Unix 环境下的 Windows 路径（应该被当作普通路径处理）."""
        with patch('os.name', 'posix'):
            # 在 Unix 环境下，Windows 路径会被当作普通路径处理
            assert _validate_path("F:/Projects/deepagents/README.md") == "/F:/Projects/deepagents/README.md"
            assert _validate_path("F:\\Projects\\deepagents\\README.md") == "/F:/Projects/deepagents/README.md"

    def test_git_bash_paths(self):
        """测试 Git Bash 路径格式."""
        # Git Bash 相对路径 (normpath 会标准化)
        assert _validate_path("./README.md") == "/README.md"  # normpath 移除 ./
        
        # Git Bash 绝对路径（Unix 风格）
        assert _validate_path("/f/Projects/deepagents/README.md") == "/f/Projects/deepagents/README.md"
        assert _validate_path("/c/Users/Admin/file.txt") == "/c/Users/Admin/file.txt"

    def test_path_traversal_protection(self):
        """测试路径遍历攻击保护."""
        with pytest.raises(ValueError, match="Path traversal not allowed"):
            _validate_path("../etc/passwd")
        
        with pytest.raises(ValueError, match="Path traversal not allowed"):
            _validate_path("../../secret")
        
        with pytest.raises(ValueError, match="Path traversal not allowed"):
            _validate_path("~/.ssh/id_rsa")

    def test_allowed_prefixes(self):
        """测试允许的前缀过滤."""
        # 正常情况
        assert _validate_path("/data/file.txt", allowed_prefixes=["/data/"]) == "/data/file.txt"
        assert _validate_path("/logs/app.log", allowed_prefixes=["/data/", "/logs/"]) == "/logs/app.log"
        
        # 不允许的前缀
        with pytest.raises(ValueError, match="Path must start with one of"):
            _validate_path("/etc/file.txt", allowed_prefixes=["/data/"])
        
        with pytest.raises(ValueError, match="Path must start with one of"):
            _validate_path("/tmp/test", allowed_prefixes=["/data/", "/logs/"])

    def test_allowed_prefixes_with_windows_paths(self):
        """测试 Windows 路径的前缀过滤."""
        with patch('os.name', 'nt'):
            # Windows 绝对路径应该能正确匹配前缀
            assert _validate_path("F:/Projects/file.txt", allowed_prefixes=["F:/Projects/"]) == "F:/Projects/file.txt"
            
            # 不匹配的前缀
            with pytest.raises(ValueError, match="Path must start with one of"):
                _validate_path("C:/Windows/file.txt", allowed_prefixes=["F:/Projects/"])

    def test_path_normalization(self):
        """测试路径标准化."""
        # 测试多余的斜杠 (在Windows上,前导 // 会被保留,这是UNC路径)
        # 我们重点测试路径中间和末尾的斜杠
        assert _validate_path("foo//bar//") == "/foo/bar"
        
        # 测试当前目录引用
        assert _validate_path("/./foo/./bar") == "/foo/bar"
        
        # 测试父目录引用（在允许范围内）
        assert _validate_path("/foo/../bar") == "/bar"

    def test_mixed_separators(self):
        """测试混合分隔符."""
        # Unix 路径中的反斜杠
        assert _validate_path("foo\\bar") == "/foo/bar"
        assert _validate_path("/foo\\bar") == "/foo/bar"
        
        # Windows 环境下的混合分隔符
        with patch('os.name', 'nt'):
            assert _validate_path("F:\\Projects/deepagents\\README.md") == "F:/Projects/deepagents/README.md"
            assert _validate_path("F:/Projects\\deepagents/README.md") == "F:/Projects/deepagents/README.md"

    def test_edge_cases(self):
        """测试边界情况."""
        # 空路径 (normpath 会将空字符串变为 '.')
        assert _validate_path("") == "/."
        
        # 根路径
        assert _validate_path("/") == "/"
        
        # 单个字符路径
        assert _validate_path("a") == "/a"
        
        # Windows 驱动器根目录
        with patch('os.name', 'nt'):
            assert _validate_path("C:\\") == "C:/"
            assert _validate_path("F:/") == "F:/"