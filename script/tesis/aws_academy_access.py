#!/usr/bin/env python3
"""Obtain Academy temporary credentials through the authorized Canvas login.

The portal password is entered interactively and is never stored. A one-time
--renew uses the documented Start Lab button; no session limit is bypassed.
"""

import argparse
import configparser
import getpass
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=True)
    parser.add_argument("--lab", choices=["183928", "185395"], default="183928")
    parser.add_argument("--renew", action="store_true")
    args = parser.parse_args()
    password = getpass.getpass("Canvas password (not stored): ")
    options = Options()
    options.add_argument("-headless")
    options.set_preference("signon.rememberSignons", False)
    driver = webdriver.Firefox(options=options)
    driver.set_page_load_timeout(45)
    driver.set_window_size(1440, 1000)
    wait = WebDriverWait(driver, 30)
    try:
        driver.get("https://awsacademy.instructure.com/login/canvas")
        wait.until(lambda d: d.find_elements(By.ID, "username"))
        driver.find_element(By.ID, "username").send_keys(args.username)
        driver.find_element(By.ID, "password").send_keys(password)
        password = None
        driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()
        wait.until(lambda d: "/login/" not in d.current_url)
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
        wait.until(
            lambda d: d.find_elements(By.CSS_SELECTOR, "iframe[id^=tool_content_]")
        )
        driver.switch_to.frame(
            driver.find_element(By.CSS_SELECTOR, "iframe[id^=tool_content_]")
        )
        wait.until(lambda d: d.find_elements(By.ID, "detailbtn2"))

        def details():
            driver.find_element(By.ID, "detailbtn2").click()
            wait.until(lambda d: d.find_element(By.ID, "clikeyboxbtn").is_displayed())
            text = driver.find_element(By.TAG_NAME, "body").text
            result = {}
            for label in (
                "Remaining session time",
                "Session started at",
                "Session to end",
                "AWSAccountId",
                "Region",
            ):
                match = re.search(re.escape(label) + r"\s*:?\s*([^\n]+)", text)
                if match:
                    result[label] = match.group(1).strip()
            budget = re.search(r"Used \$([\d.]+) of \$([\d.]+)", text)
            if budget:
                result["reported_used_usd"], result["reported_budget_usd"] = map(
                    float, budget.groups()
                )
            return result

        before = details()
        driver.find_element(By.ID, "panel3-hide").click()
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
        after = details()
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
        path.parent.mkdir(mode=0o700, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        os.fchmod(fd, 0o600)
        config = configparser.ConfigParser()
        config["default"] = values
        with os.fdopen(fd, "w") as file:
            config.write(file)
        report = {
            "observed_at_utc": datetime.now(timezone.utc).isoformat(),
            "lab": args.lab,
            "renew_requested": args.renew,
            "before": before,
            "after": after,
            "credentials_file": str(path),
        }
        private = Path.home() / ".local/state/helix/aws-academy"
        private.mkdir(parents=True, exist_ok=True, mode=0o700)
        report_path = private / ("session-" + args.lab + ".json")
        fd = os.open(report_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as file:
            json.dump(report, file, indent=2)
        for snapshot in (before, after):
            if "AWSAccountId" in snapshot:
                snapshot["AWSAccountId"] = "ending " + snapshot["AWSAccountId"][-4:]
        print(json.dumps(report, indent=2))
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
