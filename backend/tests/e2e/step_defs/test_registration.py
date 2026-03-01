"""User Registration feature tests."""
import re

from playwright.sync_api import Page, expect
from pytest_bdd import given, parsers, scenarios, then, when

# Dynamically load all scenarios from the registration feature file
scenarios('../features/registration.feature')

# ==========================================
# GIVEN STEPS (Setup)
# ==========================================

@given('I am on the registration page')
def _(page: Page):
    """Navigates to the registration page before every scenario."""
    page.goto("/register")

@given(parsers.parse('a user exists with username "{username}" and password "{password}"'))
def _(create_test_user_synchronous, username, password):
    """
    Reuses your bulletproof synchronous fixture from conftest.py!
    This ensures the 'Existing Username' scenario triggers a backend error.
    """
    create_test_user_synchronous(username=username, plain_password=password)

# ==========================================
# WHEN STEPS (Actions)
# ==========================================

@when('I fill in the registration form with:')
def _(page: Page, datatable):
    """
    The Magic Datatable Step!
    Takes the Markdown table from Gherkin, converts it to a dictionary,
    and drives the Playwright form filling. Works for both standard
    scenarios and Scenario Outlines!
    """
    # Convert the list of lists into a standard dictionary
    # e.g., [["username", "john_doe"], ["email", "john@test.com"]] -> {"username": "john_doe", ...}
    data = dict(datatable)

    # Safely fill out the form using dictionary lookups.
    # We use exact=True on Password to avoid accidentally clicking "Confirm Password"
    if "username" in data:
        page.get_by_label("Username").fill(data["username"])

    if "full_name" in data:
        page.get_by_label("Full Name").fill(data["full_name"])

    if "email" in data:
        page.get_by_label("Email").fill(data["email"])

    if "password" in data:
        # For the main password:
        page.get_by_placeholder("Create a password").fill(data["password"])

    if "confirm" in data:
        # For the confirm password:
        page.get_by_placeholder("Confirm your password").fill(data["confirm"])

@when('I click the register button')
def _(page: Page):
    page.get_by_role("button", name="Create Account").click()
    # page.pause()  # <-- This will pause the test and open Playwright Inspector for debugging. Remove or comment out in production tests!

# ==========================================
# THEN STEPS (Assertions)
# ==========================================

@then('I should be redirected to the login page')
def _(page: Page):
    expect(page).to_have_url(re.compile(r".*/login"))

@then('I should remain on the registration page')
def _(page: Page):
    expect(page).to_have_url(re.compile(r".*/register"))

@then(parsers.parse('I should see "{message}" message'))
def _(page: Page, message: str):
    """Handles success messages (usually green toasts/alerts)."""
    expect(page.get_by_text(message)).to_be_visible()

@then(parsers.parse('I should see "{error_message}" error'))
def _(page: Page, error_message: str):
    """
    Checks for standard UI errors, and falls back to Native HTML5
    validation messages on the currently focused input.
    """
    # 1. First, check if it's a standard text error rendered in the DOM
    try:
        expect(page.get_by_text(error_message)).to_be_visible(timeout=2000)
        return  # We found it normally, test passes!
    except Exception:
        pass  # Not in the DOM, let's check for a native tooltip

    # 2. Grab the Native HTML5 validation message from the focused element
    # When a native HTML5 form fails, the browser automatically focuses the invalid field.
    native_error = page.evaluate("() => document.activeElement.validationMessage")

    if native_error:
        assert native_error == error_message, (
            f"Native tooltip mismatch! Expected: '{error_message}', "
            f"but the browser actually said: '{native_error}'"
        )
        return

    # 3. If it's totally blank, force a failure so we can see the Playwright log
    raise AssertionError(f"Could not find any error message matching: '{error_message}'")

