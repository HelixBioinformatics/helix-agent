import contextlib
import io
import json
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from selenium.common.exceptions import TimeoutException
import aws_academy_access as access


TEXT = """Remaining session time: 01:12:34
Session started at: 2026-10-12T17:18:18-0700
Session to end at: 2026-10-12T21:18:18-0700
AWSAccountId: 123456789012
Region: us-east-1
Used $2.50 of $50.00
aws_secret_access_key=synthetic-secret-never-output
aws_session_token=synthetic-token-never-output
"""


class Element:
    def __init__(self, driver, identifier):
        self.driver, self.identifier = driver, identifier
        self.text = TEXT

    def click(self):
        self.driver.clicks.append(self.identifier)

    def is_displayed(self):
        return True

    def get_attribute(self, key):
        return "Ready synthetic-token-never-output" if key == "title" else ""


class Driver:
    def __init__(self):
        self.clicks = []

    def find_elements(self, by, identifier):
        return [] if identifier == "clikeyboxbtn" else [Element(self, identifier)]

    def find_element(self, by, identifier):
        if identifier == "clikeyboxbtn":
            raise AssertionError("CLI credentials must not be requested")
        return Element(self, identifier)

    def set_page_load_timeout(self, *_):
        pass

    def set_window_size(self, *_):
        pass

    def get(self, *_):
        pass

    def quit(self):
        pass


class Wait:
    def __init__(self, driver):
        self.driver = driver

    def until(self, predicate):
        result = predicate(self.driver)
        if not result:
            raise TimeoutException("synthetic-token-never-output")
        return result


class AcademyObservationTests(unittest.TestCase):
    def test_whitelist_masks_account_and_discards_secret_content(self):
        raw = access.parse_metadata(TEXT, "Ready")
        self.assertEqual(raw["AWSAccountId"], "123456789012")
        public = access.public_metadata(raw)
        self.assertEqual(public["AWSAccountId"], "ending 9012")
        self.assertEqual(public["reported_used_usd"], 2.5)
        self.assertEqual(public["remaining_computed_usd"], 47.5)
        self.assertEqual(public["Session to end"], "2026-10-12T21:18:18-0700")
        rendered = json.dumps(public)
        self.assertNotIn("123456789012", rendered)
        self.assertNotIn("synthetic-secret", rendered)
        self.assertNotIn("synthetic-token", rendered)

    def test_details_without_cli_button_observe_only_never_writes_or_renews(self):
        driver = Driver()
        with patch.object(access, "atomic_private_write", side_effect=AssertionError("must not write")):
            result = access.observation(driver, Wait(driver), "185395")
        self.assertEqual(driver.clicks, ["detailbtn2"])
        self.assertFalse(result["cli_credentials_opened"])
        self.assertFalse(result["private_files_written"])
        self.assertEqual(result["lifecycle_actions"], [])
        self.assertFalse(result["panel_health"]["clikeyboxbtn"]["present"])
        self.assertNotIn("synthetic-token", json.dumps(result))

    def test_missing_values_stay_absent_and_delay_is_explicitly_unverified(self):
        value = access.parse_metadata("No budget or session values available", "Stopped")
        self.assertNotIn("reported_used_usd", value)
        self.assertNotIn("Session to end", value)
        self.assertIsNone(value["usage_delay"]["displayed_amount"])
        self.assertFalse(value["usage_delay"]["independently_verified"])
        self.assertEqual(value["lab_status"], "stopped_or_not_ready")

    def test_credential_session_metadata_rejects_partial_binding(self):
        partial = access.parse_metadata("Remaining session time: 01:12:34", "Ready")
        with patch.object(access, "metadata_snapshot", return_value=partial):
            with self.assertRaises(TimeoutException):
                access.credential_metadata(Driver(), Wait(Driver()))

    def test_credential_session_metadata_waits_for_hydrated_fields(self):
        partial = access.parse_metadata("Remaining session time: 01:12:34", "Ready")
        complete = access.parse_metadata(TEXT, "Ready")

        class HydrationWait(Wait):
            def until(self, predicate):
                if not predicate(self.driver):
                    return super().until(predicate)
                raise AssertionError("Partial metadata must not be accepted")

        with patch.object(access, "metadata_snapshot", side_effect=[partial, complete]):
            value = access.credential_metadata(Driver(), HydrationWait(Driver()))
        self.assertEqual(value["AWSAccountId"], "123456789012")
        self.assertEqual(value["Session to end"], "2026-10-12T21:18:18-0700")

    def test_displayed_delay_and_number_formats(self):
        value = access.parse_metadata("Used $1,234.50 of $2,000.00\nBudget data is 8 hours old")
        self.assertEqual(value["reported_used_usd"], 1234.5)
        self.assertEqual(value["usage_delay"]["displayed_amount"], 8)
        self.assertFalse(value["usage_delay"]["independently_verified"])

    def test_nonfinite_money_is_never_serialized(self):
        value = access.parse_metadata("Used $" + "9" * 500 + " of $50")
        self.assertNotIn("reported_used_usd", value)
        json.dumps(value, allow_nan=False)

    def test_observe_renew_conflict_is_refused_before_password_or_browser(self):
        with patch("sys.argv", ["script", "--username", "synthetic-user", "--observe-only", "--renew"]), \
             patch.object(access.getpass, "getpass", side_effect=AssertionError("must not prompt")), \
             contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                access.main()
        self.assertEqual(raised.exception.code, 2)

    def test_timeout_diagnostic_has_no_body_exception_message_or_secret(self):
        captured = io.StringIO()
        with patch("sys.argv", ["script", "--username", "synthetic-user", "--observe-only"]), \
             patch.object(access.getpass, "getpass", return_value="synthetic-test-password"), \
             patch.object(access.webdriver, "Firefox", return_value=Driver()), \
             patch.object(access, "WebDriverWait", side_effect=lambda driver, *_: Wait(driver)), \
             patch.object(Wait, "until", side_effect=TimeoutException("synthetic-token-never-output")), \
             patch.object(access, "atomic_private_write", side_effect=AssertionError("must not write")), \
             contextlib.redirect_stdout(captured):
            exit_code = access.main()
        value = json.loads(captured.getvalue())
        self.assertEqual(exit_code, 2)
        self.assertEqual(value["error_type"], "TimeoutException")
        self.assertEqual(value["stage"], "login")
        self.assertNotIn("synthetic-token", captured.getvalue())
        self.assertNotIn("body", value)

    def test_private_write_is_atomic_and_owner_only_with_failure_preserving_previous(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "private-report"
            file.write_text("previous")
            with patch.object(access.os, "replace", side_effect=OSError("simulated rename failure")):
                with self.assertRaises(OSError):
                    access.atomic_private_write(file, "incomplete replacement")
            self.assertEqual(file.read_text(), "previous")
            self.assertEqual(list(Path(directory).iterdir()), [file])
            access.atomic_private_write(file, "completed replacement")
            self.assertEqual(file.read_text(), "completed replacement")
            self.assertEqual(stat.S_IMODE(file.stat().st_mode), 0o600)


if __name__ == "__main__":
    unittest.main()
