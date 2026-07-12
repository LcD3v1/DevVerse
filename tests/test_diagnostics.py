from __future__ import annotations

import unittest

from bot.diagnostics import DiagnosticReport, format_report


class DiagnosticsTests(unittest.TestCase):
    def test_format_report_never_requires_secret_values(self) -> None:
        report = DiagnosticReport(ok=True)
        report.add("Env DISCORD_TOKEN", "ok", "configurado")
        output = format_report(report)
        self.assertIn("Env DISCORD_TOKEN", output)
        self.assertIn("configurado", output)
        self.assertNotIn("Bot ", output)

    def test_error_marks_report_as_attention(self) -> None:
        report = DiagnosticReport(ok=True)
        report.add("Banco SQLite", "erro", "OperationalError")
        self.assertFalse(report.ok)
        self.assertIn("ATENCAO", format_report(report))


if __name__ == "__main__":
    unittest.main()
