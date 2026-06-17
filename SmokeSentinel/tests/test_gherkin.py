"""
tests/test_gherkin.py
Unit tests for the gherkin module — runs fully offline (no LLM call).
Run with: pytest tests/test_gherkin.py -v
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Make sure the project root is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from gherkin.parser import (
    GherkinValidationError,
    parse,
)
from gherkin.prompt_builder import build_user_prompt, load_system_prompt
from gherkin.writer import write
from gherkin.generator import GherkinGenerator, _slugify


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_GHERKIN = """\
Feature: User Login
  Allows users to authenticate with email and password.

  @smoke @login @happy_path
  Scenario: Successful login with valid credentials
    Given the user is on the login page
    When the user enters a valid email and password
    And clicks the login button
    Then the user is redirected to the dashboard
    And a welcome message is displayed

  @smoke @login @error
  Scenario: Login fails with incorrect password
    Given the user is on the login page
    When the user enters a valid email and an incorrect password
    And clicks the login button
    Then an error message "Invalid credentials" is displayed
    And the user remains on the login page

  @smoke @login @error
  Scenario: Login fails with empty fields
    Given the user is on the login page
    When the user clicks the login button without entering any credentials
    Then validation errors are shown for both email and password fields

  @smoke @login @edge_case
  Scenario: Login page is inaccessible after session expires
    Given the user was previously logged in
    And the session has expired
    When the user tries to access the dashboard directly
    Then the user is redirected to the login page
    And a "Session expired" message is displayed
"""

MISSING_HAPPY_PATH = """\
Feature: User Login
  @smoke @login @error
  Scenario: Login fails with incorrect password
    Given the user is on the login page
    When the user enters wrong credentials
    Then an error is shown

  @smoke @login @error
  Scenario: Login fails with empty fields
    Given the user is on the login page
    When the user submits empty form
    Then validation errors are shown

  @smoke @login @edge_case
  Scenario: Session expiry
    Given the session has expired
    When the user visits the dashboard
    Then they are redirected to login
"""

MISSING_ERROR_SCENARIO = """\
Feature: User Login
  @smoke @login @happy_path
  Scenario: Successful login
    Given the user is on the login page
    When the user enters valid credentials
    Then the user sees the dashboard

  @smoke @login @happy_path
  Scenario: Remember me checkbox
    Given the user is on the login page
    When the user checks remember me and logs in
    Then the session persists

  @smoke @login @edge_case
  Scenario: Session expiry
    Given the session expired
    When the user visits a protected page
    Then they are redirected to login
"""


# ---------------------------------------------------------------------------
# parser.py tests
# ---------------------------------------------------------------------------

class TestParser:

    def test_valid_gherkin_parses_correctly(self):
        feature = parse(VALID_GHERKIN)
        assert feature.title == "User Login"
        assert len(feature.scenarios) == 4

    def test_happy_path_detected(self):
        feature = parse(VALID_GHERKIN)
        assert any(s.is_happy_path for s in feature.scenarios)

    def test_error_scenario_detected(self):
        feature = parse(VALID_GHERKIN)
        assert any(s.is_error for s in feature.scenarios)

    def test_edge_case_detected(self):
        feature = parse(VALID_GHERKIN)
        assert any(s.is_edge_case for s in feature.scenarios)

    def test_steps_parsed(self):
        feature = parse(VALID_GHERKIN)
        happy = next(s for s in feature.scenarios if s.is_happy_path)
        keywords = [step.keyword for step in happy.steps]
        assert "Given" in keywords
        assert "When" in keywords
        assert "Then" in keywords

    def test_tags_extracted(self):
        feature = parse(VALID_GHERKIN)
        happy = next(s for s in feature.scenarios if s.is_happy_path)
        assert "@smoke" in happy.tags
        assert "@login" in happy.tags
        assert "@happy_path" in happy.tags

    def test_markdown_fences_stripped(self):
        wrapped = f"```gherkin\n{VALID_GHERKIN}\n```"
        feature = parse(wrapped)
        assert feature.title == "User Login"

    def test_missing_feature_raises(self):
        with pytest.raises(GherkinValidationError, match="Feature"):
            parse("Scenario: something\n  Given a step\n  When action\n  Then result")

    def test_missing_happy_path_raises(self):
        with pytest.raises(GherkinValidationError, match="happy path"):
            parse(MISSING_HAPPY_PATH)

    def test_missing_error_scenario_raises(self):
        with pytest.raises(GherkinValidationError, match="error"):
            parse(MISSING_ERROR_SCENARIO)

    def test_empty_response_raises(self):
        with pytest.raises(GherkinValidationError, match="empty"):
            parse("")

    def test_too_few_scenarios_raises(self):
        minimal = """\
Feature: X
  @smoke @x @happy_path
  Scenario: Only one
    Given something
    When action
    Then result
"""
        with pytest.raises(GherkinValidationError, match="at least 3"):
            parse(minimal)

    def test_tags_property_on_feature(self):
        feature = parse(VALID_GHERKIN)
        assert "@smoke" in feature.tags
        assert "@happy_path" in feature.tags
        assert "@error" in feature.tags


# ---------------------------------------------------------------------------
# writer.py tests
# ---------------------------------------------------------------------------

class TestWriter:

    def test_writes_feature_file(self, tmp_path):
        feature = parse(VALID_GHERKIN)
        out = tmp_path / "login.feature"
        result_path = write(feature, out)
        assert result_path.exists()
        content = result_path.read_text()
        assert "Feature: User Login" in content

    def test_creates_parent_directories(self, tmp_path):
        feature = parse(VALID_GHERKIN)
        out = tmp_path / "a" / "b" / "c" / "login.feature"
        write(feature, out)
        assert out.exists()

    def test_output_contains_all_scenarios(self, tmp_path):
        feature = parse(VALID_GHERKIN)
        out = tmp_path / "login.feature"
        write(feature, out)
        content = out.read_text()
        for scenario in feature.scenarios:
            assert scenario.title in content

    def test_output_contains_tags(self, tmp_path):
        feature = parse(VALID_GHERKIN)
        out = tmp_path / "login.feature"
        write(feature, out)
        content = out.read_text()
        assert "@smoke" in content
        assert "@happy_path" in content

    def test_roundtrip_is_parseable(self, tmp_path):
        """Write then re-parse — should still validate cleanly."""
        feature = parse(VALID_GHERKIN)
        out = tmp_path / "login.feature"
        write(feature, out)
        re_parsed = parse(out.read_text())
        assert re_parsed.title == feature.title
        assert len(re_parsed.scenarios) == len(feature.scenarios)


# ---------------------------------------------------------------------------
# prompt_builder.py tests
# ---------------------------------------------------------------------------

class TestPromptBuilder:

    def test_system_prompt_loads(self):
        prompt = load_system_prompt()
        assert "Gherkin" in prompt
        assert "Given" in prompt

    def test_user_prompt_contains_title(self):
        prompt = build_user_prompt("User Login", "Some description", ["AC1", "AC2"])
        assert "User Login" in prompt

    def test_user_prompt_contains_ac(self):
        prompt = build_user_prompt("User Login", "", ["Must show error on wrong password"])
        assert "Must show error on wrong password" in prompt

    def test_user_prompt_handles_empty_ac(self):
        prompt = build_user_prompt("User Login", "", [])
        assert "none provided" in prompt

    def test_user_prompt_handles_empty_description(self):
        prompt = build_user_prompt("User Login", "", ["AC1"])
        assert "no description provided" in prompt


# ---------------------------------------------------------------------------
# generator.py tests (LLM mocked)
# ---------------------------------------------------------------------------

class TestGenerator:

    def _make_generator(self) -> GherkinGenerator:
        """Create a GherkinGenerator with a mock backend — no LLM call, no API key needed."""
        from gherkin.backends import LLMBackend

        class MockBackend(LLMBackend):
            def complete(self, system_prompt, user_prompt, max_tokens=2048):
                return ""  # overridden per-test via gen._backend.complete = MagicMock(...)

        gen = GherkinGenerator(backend=MockBackend())
        return gen

    def test_run_success(self, tmp_path):
        gen = self._make_generator()
        gen._backend.complete = MagicMock(return_value=VALID_GHERKIN)

        result = gen.run(
            story_title="User Login",
            story_description="As a user I want to log in.",
            acceptance_criteria=["AC1: valid login redirects to dashboard"],
            output_path=str(tmp_path / "login.feature"),
        )

        assert result.feature_file.exists()
        assert len(result.scenarios) == 4
        assert "@smoke" in result.tags

    def test_run_creates_json_metadata(self, tmp_path):
        gen = self._make_generator()
        gen._backend.complete = MagicMock(return_value=VALID_GHERKIN)

        result = gen.run(
            story_title="User Login",
            output_path=str(tmp_path / "login.feature"),
        )

        meta = tmp_path / "login.json"
        assert meta.exists()
        data = json.loads(meta.read_text())
        assert data["feature"] == "User Login"
        assert data["scenario_count"] == 4

    def test_retry_on_invalid_output(self, tmp_path):
        gen = self._make_generator()

        # First call returns garbage, second returns valid Gherkin
        gen._backend.complete = MagicMock(side_effect=["not valid gherkin at all", VALID_GHERKIN])

        result = gen.run(
            story_title="User Login",
            output_path=str(tmp_path / "login.feature"),
        )

        assert gen._backend.complete.call_count == 2
        assert result.feature.title == "User Login"

    def test_raises_after_max_retries(self, tmp_path):
        gen = self._make_generator()
        gen._backend.complete = MagicMock(return_value="not valid gherkin at all")

        with pytest.raises(GherkinValidationError):
            gen.run(
                story_title="User Login",
                output_path=str(tmp_path / "login.feature"),
            )

    def test_output_path_auto_slug(self, tmp_path):
        gen = self._make_generator()
        gen._backend.complete = MagicMock(return_value=VALID_GHERKIN)

        with patch("gherkin.generator.DEFAULT_OUTPUT_DIR", str(tmp_path)):
            result = gen.run(story_title="User Login")

        assert "user_login" in str(result.feature_file)

    def test_output_path_from_story_id(self, tmp_path):
        gen = self._make_generator()
        gen._backend.complete = MagicMock(return_value=VALID_GHERKIN)

        with patch("gherkin.generator.DEFAULT_OUTPUT_DIR", str(tmp_path)):
            result = gen.run(story_title="User Login", story_id="SMOKE-42")

        assert "SMOKE-42" in str(result.feature_file)

    def test_result_to_json(self, tmp_path):
        gen = self._make_generator()
        gen._backend.complete = MagicMock(return_value=VALID_GHERKIN)

        result = gen.run(
            story_title="User Login",
            output_path=str(tmp_path / "login.feature"),
        )

        data = result.to_json()
        assert isinstance(data["scenarios"], list)
        assert data["scenarios"][0]["steps"]


# ---------------------------------------------------------------------------
# Utility tests
# ---------------------------------------------------------------------------

class TestSlugify:
    def test_basic(self):
        assert _slugify("User Login") == "user_login"

    def test_special_chars(self):
        assert _slugify("User Login (v2)!") == "user_login_v2"

    def test_long_slug_truncated(self):
        long = "a" * 100
        assert len(_slugify(long)) <= 60
