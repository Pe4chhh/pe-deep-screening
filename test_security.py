import asyncio
import unittest
from unittest.mock import patch

import server


class UrlSafetyTests(unittest.TestCase):
    def test_rejects_local_and_private_addresses(self):
        self.assertFalse(asyncio.run(server._is_safe_public_url("http://127.0.0.1/")))
        self.assertFalse(asyncio.run(server._is_safe_public_url("http://169.254.169.254/latest/meta-data/")))
        self.assertFalse(asyncio.run(server._is_safe_public_url("file:///etc/passwd")))

    def test_allows_hostname_only_when_dns_is_public(self):
        with patch("server.socket.getaddrinfo", return_value=[(None, None, None, None, ("93.184.216.34", 443))]):
            self.assertTrue(asyncio.run(server._is_safe_public_url("https://example.com")))
        with patch("server.socket.getaddrinfo", return_value=[(None, None, None, None, ("10.0.0.3", 443))]):
            self.assertFalse(asyncio.run(server._is_safe_public_url("https://internal.example.com")))


class ReportSafetyTests(unittest.TestCase):
    def test_sanitizer_preserves_formatting_and_removes_executable_markup(self):
        fragment = '<p class="note-box other">Hello <strong>world</strong></p><script>alert(1)</script><a href="javascript:alert(2)">bad</a>'
        result = server._sanitize_html_fragment(fragment)
        self.assertIn("<strong>world</strong>", result)
        self.assertIn('class="note-box"', result)
        self.assertNotIn("other", result)
        self.assertNotIn("script", result)
        self.assertNotIn("javascript:", result)
        self.assertIn('href="#"', result)

    def test_report_escapes_text_and_serializes_chart_label(self):
        company_name = '</script><script>alert("x")</script>'
        result = server.fill_report_template(
            company_name,
            {
                "exec_summary": '<img src=x onerror="alert(1)">',
                "sec1_content": '<p>safe</p><script>alert(2)</script>',
            },
        )
        self.assertNotIn('<script>alert("x")</script>', result)
        self.assertNotIn('<img src=x onerror=', result)
        self.assertNotIn("<script>alert(2)</script>", result)
        self.assertIn("&lt;img src=x onerror=&quot;alert(1)&quot;&gt;", result)
        self.assertIn("grade-badge grade-c", result)


if __name__ == "__main__":
    unittest.main()
