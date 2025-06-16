#!/usr/bin/env python3
"""Comprehensive test runner to generate structured failure analysis."""

import json
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path


class TestResult:
    def __init__(
        self,
        file_path: str,
        test_name: str,
        status: str,
        error_type: str = None,
        error_message: str = None,
        duration: float = 0.0,
    ):
        self.file_path = file_path
        self.test_name = test_name
        self.status = status  # PASSED, FAILED, ERROR, TIMEOUT, SKIPPED
        self.error_type = error_type
        self.error_message = error_message
        self.duration = duration

    def get_module(self) -> str:
        """Extract suspected module from test path."""
        if "api" in self.file_path:
            return "api"
        elif "classifier" in self.file_path:
            return "classifier"
        elif "cli" in self.file_path:
            return "cli"
        elif "scheduler" in self.file_path:
            return "scheduler"
        elif "scraper" in self.file_path:
            return "scraper"
        elif "storage" in self.file_path:
            return "storage"
        elif "slack" in self.file_path:
            return "notification"
        elif "config" in self.file_path:
            return "config"
        elif "utils" in self.file_path:
            return "utils"
        else:
            return "unknown"


class ComprehensiveTestRunner:
    def __init__(self):
        self.test_files = self._discover_test_files()
        self.results: list[TestResult] = []
        self.timeouts = []

    def _discover_test_files(self) -> list[str]:
        """Discover all test files."""
        test_dir = Path("tests")
        return [str(f) for f in test_dir.glob("test_*.py")]

    def run_single_test_file(
        self, test_file: str, timeout: int = 60
    ) -> list[TestResult]:
        """Run a single test file with timeout."""
        print(f"📝 Running {test_file}...")

        start_time = time.time()
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    test_file,
                    "-v",
                    "--tb=short",
                    "--no-header",
                    "-q",
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            duration = time.time() - start_time
            return self._parse_test_output(
                test_file, result.stdout, result.stderr, duration
            )

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            print(f"⏰ {test_file} timed out after {duration:.1f}s")
            self.timeouts.append(test_file)
            return [
                TestResult(
                    test_file,
                    "TIMEOUT",
                    "TIMEOUT",
                    "TimeoutError",
                    f"Test file timed out after {timeout}s",
                    duration,
                )
            ]

        except Exception as e:
            duration = time.time() - start_time
            print(f"❌ {test_file} failed to run: {e}")
            return [
                TestResult(test_file, "ERROR", "ERROR", "RunnerError", str(e), duration)
            ]

    def _parse_test_output(
        self, test_file: str, stdout: str, stderr: str, duration: float
    ) -> list[TestResult]:
        """Parse pytest output to extract test results."""
        results = []

        # Parse individual test results from stdout
        test_pattern = r"(.+)::(.*?)::(.*?) (PASSED|FAILED|ERROR|SKIPPED)"

        for match in re.finditer(test_pattern, stdout):
            file_path, class_name, test_name, status = match.groups()
            full_test_name = f"{class_name}::{test_name}" if class_name else test_name

            error_type = None
            error_message = None

            if status in ["FAILED", "ERROR"]:
                # Try to extract error type from stderr or stdout
                error_match = re.search(
                    rf"{test_name}.*?(\w+Error|AssertionError|Exception)[:)]",
                    stderr + stdout,
                )
                if error_match:
                    error_type = error_match.group(1)

                # Extract error message
                error_msg_match = re.search(r"E\s+(.+)", stderr + stdout)
                if error_msg_match:
                    error_message = error_msg_match.group(1)[:100]  # Truncate

            results.append(
                TestResult(
                    test_file,
                    full_test_name,
                    status,
                    error_type,
                    error_message,
                    duration,
                )
            )

        # If no individual tests found but we have output, create a summary result
        if not results:
            if "FAILED" in stdout or "ERROR" in stdout:
                results.append(
                    TestResult(
                        test_file,
                        "FILE_LEVEL",
                        "FAILED",
                        "ParseError",
                        "Could not parse individual test results",
                        duration,
                    )
                )
            elif "passed" in stdout:
                results.append(
                    TestResult(test_file, "FILE_LEVEL", "PASSED", None, None, duration)
                )
            else:
                results.append(
                    TestResult(
                        test_file,
                        "FILE_LEVEL",
                        "UNKNOWN",
                        "UnknownError",
                        "Unknown test outcome",
                        duration,
                    )
                )

        return results

    def run_all_tests(self) -> None:
        """Run all test files."""
        print("🚀 Starting comprehensive test analysis...")
        print(f"📋 Found {len(self.test_files)} test files")
        print("=" * 60)

        for test_file in self.test_files:
            file_results = self.run_single_test_file(test_file, timeout=30)
            self.results.extend(file_results)

            # Print summary for this file
            passed = sum(1 for r in file_results if r.status == "PASSED")
            failed = sum(1 for r in file_results if r.status == "FAILED")
            errors = sum(1 for r in file_results if r.status == "ERROR")
            timeouts = sum(1 for r in file_results if r.status == "TIMEOUT")

            print(f"📊 {test_file}: {passed}✅ {failed}❌ {errors}🔥 {timeouts}⏰")

    def generate_failure_matrix(self) -> dict:
        """Generate structured failure analysis matrix."""

        # Count by status
        status_counts = Counter(r.status for r in self.results)

        # Count by error type
        error_types = Counter(r.error_type for r in self.results if r.error_type)

        # Count by module
        module_counts = defaultdict(
            lambda: {"PASSED": 0, "FAILED": 0, "ERROR": 0, "TIMEOUT": 0}
        )
        for result in self.results:
            module = result.get_module()
            module_counts[module][result.status] += 1

        # Group failures by suspected root cause
        root_cause_analysis = defaultdict(list)
        for result in self.results:
            if result.status in ["FAILED", "ERROR"]:
                module = result.get_module()
                key = f"{module}_{result.error_type or 'Unknown'}"
                root_cause_analysis[key].append(
                    {
                        "test": result.test_name,
                        "file": result.file_path,
                        "error": result.error_message,
                    }
                )

        # Priority recommendations
        priority_recommendations = self._generate_priority_recommendations(
            error_types, module_counts, root_cause_analysis
        )

        return {
            "summary": {
                "total_tests": len(self.results),
                "by_status": dict(status_counts),
                "by_error_type": dict(error_types),
                "timeout_files": self.timeouts,
            },
            "module_breakdown": dict(module_counts),
            "root_cause_analysis": dict(root_cause_analysis),
            "priority_recommendations": priority_recommendations,
            "blocking_issues": self._identify_blocking_issues(),
        }

    def _generate_priority_recommendations(
        self, error_types: Counter, module_counts: dict, root_causes: dict
    ) -> dict:
        """Generate orchestration priority recommendations."""

        quick_wins = []
        complex_fixes = []

        # Analyze error patterns
        for error_type, count in error_types.most_common():
            if error_type in ["ImportError", "ModuleNotFoundError"]:
                quick_wins.append(f"Fix {count} import issues ({error_type})")
            elif error_type in ["AssertionError", "AttributeError"]:
                quick_wins.append(f"Fix {count} assertion/attribute issues")
            elif error_type in ["TimeoutError", "ConnectionError"]:
                complex_fixes.append(f"Fix {count} timeout/connection issues")
            else:
                complex_fixes.append(f"Investigate {count} {error_type} issues")

        # Analyze module impact
        high_impact_modules = []
        for module, counts in module_counts.items():
            total_issues = counts["FAILED"] + counts["ERROR"] + counts["TIMEOUT"]
            if total_issues > 5:
                high_impact_modules.append(f"{module} ({total_issues} issues)")

        return {
            "quick_wins": quick_wins[:5],  # Top 5
            "complex_fixes": complex_fixes[:5],
            "high_impact_modules": high_impact_modules,
            "recommended_order": [
                "1. Fix import/dependency issues",
                "2. Address configuration problems",
                "3. Fix API/auth issues",
                "4. Address async/timeout issues",
                "5. Fix component integration issues",
            ],
        }

    def _identify_blocking_issues(self) -> list[str]:
        """Identify issues that block parallel fixing."""
        blocking = []

        # Check for widespread import issues
        import_errors = sum(
            1
            for r in self.results
            if r.error_type in ["ImportError", "ModuleNotFoundError"]
        )
        if import_errors > 10:
            blocking.append("Widespread import issues prevent parallel development")

        # Check for timeout files
        if len(self.timeouts) > 2:
            blocking.append(
                f"{len(self.timeouts)} test files timing out - infrastructure issue"
            )

        # Check for configuration issues
        config_errors = sum(
            1 for r in self.results if "config" in r.file_path and r.status != "PASSED"
        )
        if config_errors > 3:
            blocking.append("Configuration system issues affect multiple modules")

        return blocking

    def save_report(self, filename: str = "test_failure_analysis.json") -> None:
        """Save comprehensive analysis to JSON file."""
        matrix = self.generate_failure_matrix()

        with open(filename, "w") as f:
            json.dump(matrix, f, indent=2)

        print(f"\n📄 Detailed analysis saved to {filename}")

    def print_summary(self) -> None:
        """Print executive summary for orchestration planning."""
        matrix = self.generate_failure_matrix()

        print("\n" + "=" * 80)
        print("📊 COMPREHENSIVE TEST FAILURE ANALYSIS")
        print("=" * 80)

        summary = matrix["summary"]
        print("📈 OVERALL STATS:")
        print(f"   Total Tests: {summary['total_tests']}")
        for status, count in summary["by_status"].items():
            emoji = {
                "PASSED": "✅",
                "FAILED": "❌",
                "ERROR": "🔥",
                "TIMEOUT": "⏰",
            }.get(status, "❓")
            print(f"   {status}: {count} {emoji}")

        print("\n🔥 TOP ERROR TYPES:")
        for error_type, count in summary["by_error_type"].items():
            print(f"   {error_type}: {count}")

        print("\n🏗️ MODULE BREAKDOWN:")
        for module, counts in matrix["module_breakdown"].items():
            total_issues = counts["FAILED"] + counts["ERROR"] + counts["TIMEOUT"]
            if total_issues > 0:
                print(
                    f"   {module}: {counts['PASSED']}✅ {counts['FAILED']}❌ {counts['ERROR']}🔥 {counts['TIMEOUT']}⏰"
                )

        print("\n🚀 ORCHESTRATION RECOMMENDATIONS:")
        for i, rec in enumerate(
            matrix["priority_recommendations"]["recommended_order"], 1
        ):
            print(f"   {rec}")

        print("\n⚠️ BLOCKING ISSUES:")
        for issue in matrix["blocking_issues"]:
            print(f"   • {issue}")

        if matrix["blocking_issues"]:
            print(
                "\n🎯 RECOMMENDED WORKFLOW: Debug → Code → Test (address blocking issues first)"
            )
        else:
            print(
                "\n🎯 RECOMMENDED WORKFLOW: Parallel Debug/Code → Test (no major blockers)"
            )


def main():
    runner = ComprehensiveTestRunner()
    runner.run_all_tests()
    runner.save_report()
    runner.print_summary()


if __name__ == "__main__":
    main()
