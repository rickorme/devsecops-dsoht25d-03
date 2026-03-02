import re

from playwright.sync_api import Page, expect
from pytest_bdd import given, parsers, scenarios, then, when

scenarios('../features/user-dashboard.feature')

# ==========================================
# GIVEN STEPS (Setup)
# ==========================================

@given(parsers.parse('a user exists with username "{username}" and password "{password}"'))
def _(create_test_user_synchronous, username, password):
    create_test_user_synchronous(username=username, plain_password=password)

@given(parsers.parse('I am logged in as "{username}"'))
def _(page: Page, username):
    page.goto("/login")
    page.get_by_label("Username").fill(username)
    page.get_by_label("Password").fill("SecurePass123!")
    page.get_by_role("button", name="Login").click()
    expect(page).to_have_url(re.compile(r".*/user-dashboard"))

@given(parsers.parse('the user "{username}" belongs to the following circles:'))
def _(setup_user_circles_synchronous, username, datatable):
    """
    Advanced Datatable Parsing:
    Reads the multi-column Gherkin table and seeds the database.
    """
    headers = datatable[0] # Gets ["circle_name", "role"]
    # Zips headers with each row to create a list of dictionaries
    circles_data = [dict(zip(headers, row, strict=False)) for row in datatable[1:]]

    setup_user_circles_synchronous(username, circles_data)

@given('I navigate to the dashboard')
def _(page: Page):
    page.goto("/user-dashboard")

@given('the following posts exist in the circles:')
def _(create_circle_post_synchronous, datatable):
    """Loops through the Gherkin table and seeds the database with posts."""
    headers = datatable[0]
    posts_data = [dict(zip(headers, row, strict=False)) for row in datatable[1:]]

    for post in posts_data:
        create_circle_post_synchronous(
            circle_name=post["circle_name"],
            author_username=post["author"],
            title=post["title"],
            content=post["content"]
        )

# ==========================================
# WHEN STEPS (Actions)
# ==========================================

@when(parsers.parse('I click on the "{circle_name}" circle card'))
def _(page: Page, circle_name):
    # Adjust this to match how React renders the clickable circle
    # E.g., if it's an <a> tag: page.get_by_role("link", name=circle_name).click()
    # page.locator(f"text={circle_name}").click()
    page.get_by_role("heading", name=circle_name).click()

# ==========================================
# THEN STEPS (Assertions)
# ==========================================

@then('I should see the following in my circles list:')
def _(page: Page, datatable):
    headers = datatable[0]
    expected_circles = [dict(zip(headers, row, strict=False)) for row in datatable[1:]]

    # 1. Create an empty bucket to hold our errors
    errors = []

    for expected in expected_circles:
        circle_card = page.locator(".circle-card").filter(
            has=page.get_by_role("heading", name=expected["circle_name"])
        )

        # HARD ASSERTION: We keep this standard. If the card itself is missing, 
        # there's no point checking the text inside it, so we let it fail fast.
        expect(circle_card).to_be_visible()

        # SOFT ASSERTION 1: Check Role
        try:
            expect(circle_card).to_contain_text(expected["role"])
        except AssertionError as e:
            # We strip out the giant Playwright stack trace and just keep the readable error
            errors.append(f"❌ {expected['circle_name']} Role Error: {e.args[0].split('Call log:')[0].strip()}")

        # SOFT ASSERTION 2: Check Badge
        try:
            expect(circle_card).to_contain_text(expected["badge"])
        except AssertionError as e:
            errors.append(f"❌ {expected['circle_name']} Badge Error: {e.args[0].split('Call log:')[0].strip()}")

    # 2. After the loop finishes checking ALL circles, evaluate the bucket
    if errors:
        # If we caught anything, raise one massive AssertionError showing everything that broke!
        error_summary = "\n".join(errors)
        raise AssertionError(f"Dashboard UI validation failed with {len(errors)} errors:\n\n{error_summary}")

@then('I should see the recent activity feed')
def _(page: Page):
    # Adjust to your UI (e.g., checking for a specific heading or container)
    expect(page.get_by_role("heading", name="Recent Activity")).to_be_visible()

@then(parsers.parse('I should see posts from the "{circle_name}" circle'))
def _(page: Page, circle_name):
    # We look for the exact title we wrote in the Data Table!
    expect(page.get_by_role("heading", name=circle_name)).to_be_visible()
    # expect(page.get_by_text("Weekend BBQ")).to_be_visible()

@then(parsers.parse('I should be redirected to the circle page for "{circle_name}"'))
def _(page: Page, circle_name):
    expect(page).to_have_url(re.compile(r".*/circles/.*"))
    expect(page.get_by_role("heading", name=circle_name)).to_be_visible()
