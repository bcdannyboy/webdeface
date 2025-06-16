"""Test runner for Slack command test suite with coverage reporting."""

import os
import subprocess
import sys
from pathlib import Path


def run_slack_tests():
    """Run the comprehensive Slack command test suite."""

    # Get the project root directory
    project_root = Path(__file__).parent.parent.parent
    slack_tests_dir = Path(__file__).parent

    print("🧪 Running Slack Command Test Suite")
    print("=" * 50)
    print(f"Project Root: {project_root}")
    print(f"Test Directory: {slack_tests_dir}")
    print("=" * 50)

    # Set environment variables for testing
    env = os.environ.copy()
    env.update(
        {"PYTHONPATH": str(project_root), "TESTING": "true", "SLACK_TEST_MODE": "true"}
    )

    # Test commands to run
    test_commands = [
        # Run all tests with coverage
        [
            sys.executable,
            "-m",
            "pytest",
            str(slack_tests_dir),
            "--cov=src/webdeface/notification/slack",
            "--cov-report=term-missing",
            "--cov-report=html:tests/slack/htmlcov",
            "--cov-report=json:tests/slack/coverage.json",
            "--cov-fail-under=90",
            "-v",
            "--tb=short",
        ],
        # Run specific test categories
        [
            sys.executable,
            "-m",
            "pytest",
            str(slack_tests_dir / "test_website_commands.py"),
            "-v",
            "--tb=short",
            "-m",
            "not slow",
        ],
        [
            sys.executable,
            "-m",
            "pytest",
            str(slack_tests_dir / "test_monitoring_commands.py"),
            "-v",
            "--tb=short",
            "-m",
            "not slow",
        ],
        [
            sys.executable,
            "-m",
            "pytest",
            str(slack_tests_dir / "test_system_commands.py"),
            "-v",
            "--tb=short",
            "-m",
            "not slow",
        ],
        [
            sys.executable,
            "-m",
            "pytest",
            str(slack_tests_dir / "test_command_router.py"),
            "-v",
            "--tb=short",
        ],
        [
            sys.executable,
            "-m",
            "pytest",
            str(slack_tests_dir / "test_parsers.py"),
            "-v",
            "--tb=short",
        ],
        [
            sys.executable,
            "-m",
            "pytest",
            str(slack_tests_dir / "test_slack_integration.py"),
            "-v",
            "--tb=short",
            "-m",
            "integration",
        ],
    ]

    print("\n📋 Test Categories:")
    print("• Website Commands (4 commands: add, remove, list, status)")
    print("• Monitoring Commands (5 commands: start, stop, pause, resume, check)")
    print("• System Commands (4 commands: status, health, metrics, logs)")
    print("• Command Router (routing, permissions, error handling)")
    print("• Command Parser (name:value flags, CLI compatibility)")
    print("• Integration Tests (end-to-end with Slack Bolt)")
    print("\n🎯 Coverage Target: ≥90%")
    print("=" * 50)

    # Run main test suite with coverage
    print("\n🚀 Running comprehensive test suite...")
    try:
        result = subprocess.run(
            test_commands[0], cwd=project_root, env=env, capture_output=False, text=True
        )

        if result.returncode == 0:
            print("\n✅ All tests passed with ≥90% coverage!")
        else:
            print(f"\n❌ Tests failed with return code: {result.returncode}")
            return False

    except Exception as e:
        print(f"\n💥 Error running tests: {e}")
        return False

    # Run individual test categories for detailed reporting
    print("\n📊 Running individual test categories...")

    test_categories = [
        ("Website Commands", test_commands[1]),
        ("Monitoring Commands", test_commands[2]),
        ("System Commands", test_commands[3]),
        ("Command Router", test_commands[4]),
        ("Command Parser", test_commands[5]),
        ("Integration Tests", test_commands[6]),
    ]

    for category_name, cmd in test_categories:
        print(f"\n🔍 Testing {category_name}...")
        try:
            result = subprocess.run(
                cmd, cwd=project_root, env=env, capture_output=True, text=True
            )

            if result.returncode == 0:
                print(f"  ✅ {category_name} - All tests passed")
            else:
                print(f"  ❌ {category_name} - Some tests failed")

        except Exception as e:
            print(f"  💥 {category_name} - Error: {e}")

    # Generate coverage summary
    print("\n📈 Generating coverage summary...")
    try:
        coverage_file = slack_tests_dir / "coverage.json"
        html_dir = slack_tests_dir / "htmlcov"

        if coverage_file.exists():
            print(f"  📄 JSON coverage report: {coverage_file}")

        if html_dir.exists():
            print(f"  🌐 HTML coverage report: {html_dir}/index.html")

    except Exception as e:
        print(f"  ⚠️  Coverage report generation error: {e}")

    print("\n🎉 Test suite execution completed!")
    print("=" * 50)

    return True


def print_test_summary():
    """Print a summary of what the test suite covers."""

    print("\n📋 SLACK COMMAND TEST SUITE SUMMARY")
    print("=" * 60)

    print("\n🎯 TEST COVERAGE TARGETS:")
    print("• ≥90% code coverage on src/webdeface/notification/slack/")
    print("• All 13 command handlers across 3 categories")
    print("• Command routing, permissions, and error handling")
    print("• Behavioral parity with CLI commands")
    print("• End-to-end integration with Slack Bolt")

    print("\n📁 TEST FILES CREATED:")
    test_files = [
        ("conftest.py", "Test fixtures and utilities"),
        ("test_website_commands.py", "Website management commands (4 commands)"),
        ("test_monitoring_commands.py", "Monitoring control commands (5 commands)"),
        ("test_system_commands.py", "System management commands (4 commands)"),
        ("test_command_router.py", "Command routing and error handling"),
        ("test_parsers.py", "Command parsing with name:value flags"),
        ("test_slack_integration.py", "End-to-end integration tests"),
        ("pytest.ini", "Test configuration"),
        ("run_tests.py", "Test runner script"),
    ]

    for filename, description in test_files:
        print(f"  • {filename:25} - {description}")

    print("\n🧪 TEST CATEGORIES:")

    categories = [
        (
            "Website Commands",
            [
                "add <url> [name:NAME] [interval:SECONDS]",
                "remove <website_id> [force:true]",
                "list [status:active|inactive|all] [format:table|json]",
                "status <website_id>",
            ],
        ),
        (
            "Monitoring Commands",
            [
                "start [website_id]",
                "stop [website_id]",
                "pause <website_id> [duration:SECONDS]",
                "resume <website_id>",
                "check <website_id>",
            ],
        ),
        (
            "System Commands",
            [
                "status",
                "health",
                "metrics [range:1h|24h|7d|30d] [type:all|performance|monitoring|alerts|system]",
                "logs [level:debug|info|warning|error] [limit:NUMBER] [since:TIME]",
            ],
        ),
    ]

    for category, commands in categories:
        print(f"\n  {category}:")
        for cmd in commands:
            print(f"    • /webdeface {cmd}")

    print("\n🔒 PERMISSION TESTING:")
    print("  • Viewer: VIEW_* permissions")
    print("  • Operator: VIEW_* + ACKNOWLEDGE_ALERTS + PAUSE_* + TRIGGER_CHECKS")
    print("  • Admin: All permissions except SYSTEM_ADMIN")
    print("  • Super Admin: All permissions")

    print("\n🛡️ ERROR HANDLING TESTING:")
    print("  • Command parsing errors")
    print("  • Validation errors with suggestions")
    print("  • Permission denied responses")
    print("  • Database/service failures")
    print("  • Timeout handling")
    print("  • Invalid arguments/flags")

    print("\n🔄 BEHAVIORAL PARITY TESTING:")
    print("  • Slack `/cmd --flag` results match `webdeface cmd --flag`")
    print("  • CLI argument conversion and parsing")
    print("  • Flag handling (name:value syntax)")
    print("  • Response formatting consistency")

    print("\n⚡ INTEGRATION TESTING:")
    print("  • Slack Bolt App(test_client=True)")
    print("  • Mock Slack client responses")
    print("  • End-to-end command execution")
    print("  • Multi-user concurrent testing")
    print("  • Complex command scenarios")

    print("\n🎨 RESPONSE FORMATTING:")
    print("  • Slack Block Kit compliance")
    print("  • Error message formatting")
    print("  • Success response formatting")
    print("  • Help system integration")

    print("=" * 60)


if __name__ == "__main__":
    print_test_summary()

    if len(sys.argv) > 1 and sys.argv[1] == "--summary-only":
        sys.exit(0)

    print("\n🚀 Starting test execution...")
    success = run_slack_tests()

    if success:
        print("\n🎉 SUCCESS: Comprehensive Slack command test suite completed!")
        print("✅ All tests passed with ≥90% coverage")
        print("✅ Behavioral parity verified")
        print("✅ Integration tests passed")
        sys.exit(0)
    else:
        print("\n❌ FAILURE: Some tests failed or coverage below 90%")
        sys.exit(1)
