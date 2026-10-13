#!/usr/bin/env python3
"""Observe Academy metadata or obtain credentials through authorized Canvas login.

The portal password is entered interactively and is never stored. A one-time
--renew uses the documented Start Lab button; no session limit is bypassed.
--observe-only does not open CLI credentials, renew a lab or write private files.
"""

import argparse
import configparser
import getpass
import json
import math
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait


PANEL_IDS = ("detailbtn2", "panel3", "panel3-hide", "clikeyboxbtn", "vmstatus", "labspinbox")


def parse_metadata(text, status_title=""):
    """Internal whitelist. The account ID is masked before any public output."""
    result = {}
    patterns = {
        "Remaining session time": r"\d{1,3}:\d{2}(?::\d{2})?",
        "Session started at": r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:?\d{2})?",
        "Session to end": r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:?\d{2})?",
        "AWSAccountId": r"\d{12}\b",
        "Region": r"[a-z]{2}(?:-[a-z]+)+-\d\b",
    }
    for label, pattern in patterns.items():
        prefix = r"\s*:?\s*(?:at\s*:?\s*)?" if label.startswith("Session ") else r"\s*:?\s*"
        label_pattern = r"\s+".join(re.escape(part) for part in label.split())
        match = re.search(label_pattern + prefix + r"(" + pattern + r")", text, re.I)
        if match:
            result[label] = match.group(1)
    budget = re.search(r"Used\s*\$\s*([\d,]+(?:\.\d+)?)\s*of\s*\$\s*([\d,]+(?:\.\d+)?)", text, re.I)
    if budget:
        used, total = (float(value.replace(",", "")) for value in budget.groups())
        if math.isfinite(used) and math.isfinite(total):
            result.update(reported_used_usd=used, reported_budget_usd=total,
                          remaining_computed_usd=round(total-used, 6))
    title = status_title.casefold()
    result["lab_status"] = next((label for pattern, label in (
        (r"not ready|not started|stopped|terminated", "stopped_or_not_ready"),
        (r"in progress|starting|initializ|pending", "starting_or_pending"),
        (r"ready|running", "ready_or_running"),
        (r"error|failed", "error"),
    ) if re.search(pattern, title)), "unknown")
    # A delay is reported only when the rendered portal actually supplies it.
    delay = re.search(r"(?:budget|usage|spend)[^\n]{0,100}?(\d+)\s*(hours?|minutes?)\s*(?:old|behind|delay)", text, re.I)
    result["usage_delay"] = {
        "displayed_amount": int(delay.group(1)) if delay else None,
        "displayed_unit": delay.group(2).lower() if delay else None,
        "independently_verified": False,
        "interpretation": "Portal-reported cumulative use; update latency and final billed use are not independently verified.",
    }
    return result


def public_metadata(value):
    result = dict(value)
    if "AWSAccountId" in result:
        result["AWSAccountId"] = "ending " + result["AWSAccountId"][-4:]
    return result


def panel_health(driver):
    """Only known control IDs and booleans, never body/HTML/cookies/tokens."""
    result = {}
    for identifier in PANEL_IDS:
        try:
            elements = driver.find_elements(By.ID, identifier)
            result[identifier] = {"present": bool(elements),
                                  "visible": any(e.is_displayed() for e in elements)}
        except Exception:
            result[identifier] = {"present": None, "visible": None}
    return result


def metadata_snapshot(driver):
    elements = driver.find_elements(By.ID, "vmstatus")
    title = elements[0].get_attribute("title") or "" if elements else ""
    return parse_metadata(driver.find_element(By.TAG_NAME, "body").text, title)


def details(driver, wait):
    driver.find_element(By.ID, "detailbtn2").click()
    # The metadata panel can be hydrated with no CLI-credential button. Waiting
    # for that unrelated button made legitimate balance observations time out.
    def available(d):
        value = metadata_snapshot(d)
        return value if any(key in value for key in (
            "Session to end", "Remaining session time", "AWSAccountId", "reported_used_usd"
        )) else False
    return wait.until(available)


def observation(driver, wait, lab):
    metadata = details(driver, wait)
    required = ("Session to end", "reported_used_usd", "reported_budget_usd")
    # Panel state and budget data hydrate asynchronously. Await the desired
    # metadata itself, not CLI credentials; retain explicit partial observations.
    def complete(d):
        value = metadata_snapshot(d)
        return value if all(key in value for key in required) else False
    try:
        metadata = WebDriverWait(driver, 8).until(complete)
    except TimeoutException:
        metadata = metadata_snapshot(driver)
    return {"schema": "aws-academy-observation/1.0", "observed_at_utc": datetime.now(timezone.utc).isoformat(),
            "lab": lab, "observe_only": True, "renew_requested": False,
            "lifecycle_actions": [], "cli_credentials_opened": False,
            "private_files_written": False, "metadata": public_metadata(metadata),
            "observation_quality": "complete" if all(key in metadata for key in required) else "partial",
            "missing_metadata_fields": [key for key in required if key not in metadata],
            "panel_health": panel_health(driver)}


def credential_metadata(driver, wait):
    """Fail before writing credentials if their companion session is incomplete."""
    required = ("Session to end", "AWSAccountId", "Region",
                "reported_used_usd", "reported_budget_usd")

    def complete(d):
        value = metadata_snapshot(d)
        return value if all(key in value for key in required) else False

    return wait.until(complete)


def before_start_metadata(driver, wait, renew):
    """A stopped lab can omit session details until the authorized Start Lab.

    This fallback never creates a session deadline or budget. Complete metadata
    is still mandatory before saving CLI credentials and before starting EC2.
    """
    try:
        return details(driver, wait)
    except TimeoutException:
        value = metadata_snapshot(driver)
        if not renew or value.get("lab_status") != "stopped_or_not_ready":
            raise
        return {**value, "session_metadata_unavailable_before_start": True}


def atomic_private_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix=".academy-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as file:
            os.fchmod(file.fileno(), 0o600)
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=True)
    parser.add_argument("--lab", choices=["183928", "185395"], default="183928")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--renew", action="store_true")
    mode.add_argument("--observe-only", action="store_true")
    args = parser.parse_args()
    password = getpass.getpass("Canvas password (not stored): ")
    options = Options()
    options.add_argument("-headless")
    options.set_preference("signon.rememberSignons", False)
    driver = webdriver.Firefox(options=options)
    driver.set_page_load_timeout(45)
    driver.set_window_size(1440, 1000)
    wait = WebDriverWait(driver, 30)
    stage = "login"
    try:
        driver.get("https://awsacademy.instructure.com/login/canvas")
        wait.until(lambda d: d.find_elements(By.ID, "username"))
        driver.find_element(By.ID, "username").send_keys(args.username)
        driver.find_element(By.ID, "password").send_keys(password)
        password = None
        driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()
        wait.until(lambda d: "/login/" not in d.current_url)
        stage = "course_modules"
        driver.get(f"https://awsacademy.instructure.com/courses/{args.lab}/modules")
        wait.until(lambda d: d.find_elements(By.CSS_SELECTOR, ".ig-title"))
        launch = next(
            e
            for e in driver.find_elements(By.TAG_NAME, "a")
            if e.is_displayed()
            and (
                "Launch AWS Academy Learner Lab" in e.text
                or "Iniciar el Laboratorio de aprendizaje" in e.text
            )
        )
        driver.get(launch.get_attribute("href"))
        stage = "learner_lab_frame"
        wait.until(
            lambda d: d.find_elements(By.CSS_SELECTOR, "iframe[id^=tool_content_]")
        )
        driver.switch_to.frame(
            driver.find_element(By.CSS_SELECTOR, "iframe[id^=tool_content_]")
        )
        wait.until(lambda d: d.find_elements(By.ID, "detailbtn2"))
        stage = "details_metadata"
        if args.observe_only:
            print(json.dumps(observation(driver, wait, args.lab), indent=2))
            return 0
        before = before_start_metadata(driver, wait, args.renew)
        close = driver.find_elements(By.ID, "panel3-hide")
        if close and close[0].is_displayed():
            close[0].click()
        if args.renew:
            driver.find_element(By.ID, "labspinbox").find_element(
                By.XPATH, ".."
            ).click()
            wait.until(
                lambda d: (
                    "Ready"
                    in (d.find_element(By.ID, "vmstatus").get_attribute("title") or "")
                )
            )
        stage = "credential_panel"
        details(driver, wait)
        wait.until(lambda d: d.find_element(By.ID, "clikeyboxbtn").is_displayed())
        after = credential_metadata(driver, wait)
        driver.find_element(By.ID, "clikeyboxbtn").click()

        def credentials(d):
            candidates = (
                [d.find_element(By.TAG_NAME, "body").text]
                + [
                    e.get_attribute("value") or ""
                    for e in d.find_elements(By.CSS_SELECTOR, "textarea,input")
                ]
                + [e.text for e in d.find_elements(By.TAG_NAME, "pre")]
            )
            values = {
                key: next(
                    (
                        m.group(1).strip()
                        for candidate in candidates
                        if (
                            m := re.search(
                                r"(?m)^\s*" + key + r"\s*=\s*(\S+)\s*$", candidate
                            )
                        )
                    ),
                    None,
                )
                for key in (
                    "aws_access_key_id",
                    "aws_secret_access_key",
                    "aws_session_token",
                )
            }
            return values if all(values.values()) else False

        values = wait.until(credentials)
        values["region"] = after.get("Region", "us-east-1")
        path = (
            Path.home()
            / ".aws"
            / (
                "helix-academy-1.credentials"
                if args.lab == "183928"
                else "helix-academy-2.credentials"
            )
        )
        config = configparser.ConfigParser()
        config["default"] = values
        from io import StringIO
        content = StringIO()
        config.write(content)
        atomic_private_write(path, content.getvalue())
        report = {
            "observed_at_utc": datetime.now(timezone.utc).isoformat(),
            "lab": args.lab,
            "renew_requested": args.renew,
            "before": before,
            "after": after,
            "credentials_file": str(path),
        }
        private = Path.home() / ".local/state/helix/aws-academy"
        report_path = private / ("session-" + args.lab + ".json")
        atomic_private_write(report_path, json.dumps(report, indent=2))
        report["before"], report["after"] = public_metadata(before), public_metadata(after)
        print(json.dumps(report, indent=2))
        return 0
    except Exception as error:
        print(json.dumps({"schema": "aws-academy-access-error/1.0",
                          "observed_at_utc": datetime.now(timezone.utc).isoformat(),
                          "lab": args.lab, "observe_only": args.observe_only,
                          "stage": stage, "error_type": type(error).__name__,
                          "panel_health": panel_health(driver)}, indent=2))
        return 2
    finally:
        driver.quit()


if __name__ == "__main__":
    raise SystemExit(main())
