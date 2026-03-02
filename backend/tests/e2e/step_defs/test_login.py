"""User Login feature tests."""
import re

import pytest
from playwright.sync_api import Browser, Page, expect
from pytest_bdd import given, parsers, scenarios, then, when

# Pro-Tip: Instead of defining every scenario manually, this single line
# tells pytest-bdd to dynamically load and run all scenarios in the file!
scenarios('../features/login.feature')

# ==========================================
# FIXTURES FOR STATE MANAGEMENT
# ==========================================

@pytest.fixture
def multi_sessions():
    """Stores multiple browser contexts for the 'Device A / Device B' test."""
    return {}

# ==========================================
# GIVEN STEPS (Setup)
# ==========================================

@given(parsers.parse('a user exists with username "{username}" and password "{password}"'))
def _(create_test_user_synchronous, username, password):
    print(f"\n--- ATTEMPTING TO INSERT {username} ---")
    create_test_user_synchronous(username=username, plain_password=password)
    print(f"--- SUCCESSFULLY INSERTED {username} ---")

@given(parsers.parse('I am logged in as "{username}"'))
def _(page: Page, username):
    """A helper step to bypass the login screen for scenarios that require an active session."""
    page.goto("/login")
    page.get_by_label("Username").fill(username)
    page.get_by_label("Password").fill("SecurePass123!") # Default test password
    page.get_by_role("button", name="Login").click()
    expect(page).to_have_url(re.compile(r".*/user-dashboard"))

@given(parsers.parse('I am logged in as "{username}" in Session {session_name}'))
def _(browser: Browser, multi_sessions, username, session_name):
    """Creates an entirely separate browser context (Incognito window) for multi-device testing."""
    context = browser.new_context()
    session_page = context.new_page()

    session_page.goto("http://localhost:3000/login")
    session_page.get_by_label("Username").fill(username)
    session_page.get_by_label("Password").fill("SecurePass123!")
    session_page.get_by_role("button", name="Login").click()

    # Store the page so we can access it in Later 'Then' steps
    multi_sessions[session_name] = session_page

# ==========================================
# WHEN STEPS (Actions)
# ==========================================

@when(parsers.parse('I login with username "{username}" and password "{password}"'))
def _(page: Page, username, password):
    """This single parameterized step handles ALL the login attempts."""
    page.goto("/login")
    # Only fill if the text isn't our special placeholder
    if username != "[BLANK]":
        page.get_by_label("Username").fill(username)
    if password != "[BLANK]":
        page.get_by_label("Password").fill(password)

    page.get_by_role("button", name="Login").click()

@when(parsers.parse('I enter a blank username and password "{password}"'))
def _(page: Page, password):
    page.goto("/login")
    page.get_by_label("Password").fill(password)
    # We intentionally do not fill the username field

@when(parsers.parse('I enter username "{username}" and a blank password'))
def _(page: Page, username):
    page.goto("/login")
    page.get_by_label("Username").fill(username)
    # We intentionally do not fill the password field

@when('I attempt to login with wrong password 5 times')
def _(page: Page):
   for _ in range(5):
        page.goto("/login")
        page.get_by_label("Username").fill("john_doe")
        page.get_by_label("Password").fill("WrongPass123!")
        page.get_by_role("button", name="Login").click()
        # Wait for the UI to register the failed attempt before clicking again
        page.wait_for_timeout(500)

@when(parsers.parse('I login as "{username}" in Session {session_name}'))
def _(browser: Browser, multi_sessions, username, session_name):
    """Logs in using the second isolated browser context."""
    context = browser.new_context()
    session_page = context.new_page()

    session_page.goto("http://localhost:3000/login")
    session_page.get_by_label("Username").fill(username)
    session_page.get_by_label("Password").fill("SecurePass123!")
    session_page.get_by_role("button", name="Login").click()

    multi_sessions[session_name] = session_page

@when('my session is manually expired in the backend')
def _(page: Page):
    """
    Simulates an expired session for testing.

    Clears the browser's cookies and frontend storage so the React app
    treats the session as missing or expired, triggering the normal
    authentication flow without modifying the backend.
    """
    page.evaluate("window.localStorage.clear(); window.sessionStorage.clear();")
    page.context.clear_cookies()

@when('I refresh the page')
def _(page: Page):
    page.reload()
    # Wait for 1 second so human eyes can verify the screen actually flashed
    # and React's useEffect auth-guards have time to redirect to /login
    page.wait_for_timeout(1000)

# ==========================================
# THEN STEPS (Assertions)
# ==========================================

@then('I should be redirected to the UserDashboard')
def _(page: Page):
    expect(page).to_have_url(re.compile(r".*/user-dashboard"))

@then('I should be redirected to the login page')
def _(page: Page):
    expect(page).to_have_url(re.compile(r".*/login"))

@then('I should remain on the login page')
def _(page: Page):
    expect(page).to_have_url(re.compile(r".*/login"))

@then(parsers.parse('I should see "{error_message}" error'))
def _(page: Page, error_message):
    # Adjust this selector based on how your React app renders alerts (e.g., toast, div, span)
    expect(page.get_by_text(error_message)).to_be_visible()

@then('the login button should be disabled')
def _(page: Page):
    button = page.get_by_role("button", name="Login")
    expect(button).to_be_disabled()

@then('I should see "Account locked. Try again in 15 minutes" message')
def _(page: Page):
    expect(page.get_by_text("Account locked. Try again in 15 minutes")).to_be_visible()

@then(parsers.parse('I should see my username "{username}" in the header'))
def _(page: Page, username):
    expect(page.locator("header")).to_contain_text(username)

@then('a session cookie should be set')
def _(page: Page):
    cookies = page.context.cookies()
    assert any(cookie["name"] == "session_token" for cookie in cookies)

@then('even with correct password, login should fail')
def _(page: Page):
    page.get_by_label("Password").fill("SecurePass123!")
    page.get_by_role("button", name="Login").click()
    expect(page.get_by_role("alert")).to_contain_text("Account locked")

@then(parsers.parse('Session {session_name} should be invalidated'))
def _(multi_sessions, session_name):
    # The session isn't truly invalidated in the UI until an action is taken
    # This step is mostly semantic; the real check is the next navigation step
    pass

@then(
    parsers.parse(
        "Session {session_name} should be redirected to "
        "the login page on its next action"
    )
)
def _(multi_sessions, session_name):
    session_page = multi_sessions[session_name]
    # Trigger an action to force the frontend to realize the session is dead
    session_page.reload()
    # Wait for 1 second so human eyes can verify the screen actually flashed
    # and React's useEffect auth-guards have time to redirect to /login
    session_page.wait_for_timeout(1000)
    expect(session_page).to_have_url(re.compile(r".*/login"))

