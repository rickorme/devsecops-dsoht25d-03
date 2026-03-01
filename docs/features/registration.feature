Feature: User Registration
  As a new user
  I want to create an account
  So that I can join Social Circles

  Business Rules:
    - Username: required, 3-50 chars, alphanumeric + underscore
    - Email: required, valid format, unique
    - Password: required, min 8 chars with 1 uppercase, 1 lowercase, 1 number, 1 special
    - Full name: optional, max 100 chars

  Background:
    # This ensures Playwright navigates to the right place before every test
    Given I am on the registration page

  @smoke @critical
  Scenario: Successful registration with valid data
    When I fill in the registration form with:
      | username   | john_doe        |
      | full_name  | John Doe        |
      | email      | john@test.com   |
      | password   | SecurePass123!  |
      | confirm    | SecurePass123!  |
    And I click the register button
    Then I should be redirected to the login page
    And I should see "Account created for john_doe! You can now login." message

  @security
  Scenario: Registration fails with an existing username
    Given a user exists with username "john_doe" and password "SecurePass123!"
    When I fill in the registration form with:
      | username   | john_doe        |
      | full_name  | New Guy         |
      | email      | newguy@test.com |
      | password   | SecurePass123!  |
      | confirm    | SecurePass123!  |
    And I click the register button
    Then I should see "Username already taken" error
    And I should remain on the registration page

  @security @validation
  Scenario Outline: Form validation catches invalid inputs
    When I fill in the registration form with:
      | username   | <username>   |
      | full_name  | John Doe     |
      | email      | <email>      |
      | password   | <password>   |
      | confirm    | <confirm>    |
    And I click the register button
    Then I should see "<error_message>" error

    Examples:
      | username | email           | password       | confirm        | error_message                                                                            |
      | valid_u  | valid@test.com  | SecurePass123! | DifferentPass! | Passwords do not match                                                                   |
      | valid_u  | invalid-email   | SecurePass123! | SecurePass123! | Please include an '@' in the email address. 'invalid-email' is missing an '@'.                                                                   |
      | valid_u  | valid@test.com  | weak           | weak           | Please lengthen this text to 8 characters or more (you are currently using 4 characters).                                                   |
      | valid_u  | valid@test.com  | weakpass123    | weakpass123    | Password must include at least one upper and lower case letter, a number and a special character |