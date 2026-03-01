#feature/circle-role.feature
Feature: Circle Roles
  As a circle owner
  I want to assign roles within my circle
  So that members have appropriate permissions

  Background:
    Given the following users exist:
      | username | 
      | alice    | 
      | bob      | 
      | charlie  | 
    And alice creates a circle called "Book Club"

  @documentation
  Scenario: Circle role permissions reference
    Given circle "Book Club" exists
    Then the following roles exist in the circle:
      | role        | permissions                                      |
      | Member      | View posts, Create posts, Comment, Like          |
      | Moderator   | All Member + Delete posts, Remove members, Approve join requests |
      | Owner       | All Moderator + Delete circle, Assign roles, Change settings |

  @circle_owner @critical @todo
  Scenario: Owner has full circle control
    Given I am logged in as alice
    And I am the owner of circle "Book Club"
    When I view the circle settings
    Then I should see "👑 Owner" badge
    And I should be able to:
      | action                 |
      | delete_circle          |
      | change_circle_name     |
      | change_circle_privacy  |
      | assign_moderator       |
      | remove_member          |

  @circle_owner
  Scenario: Owner can assign moderator role
    Given I am logged in as alice
    When I assign bob as moderator of circle "Book Club"
    Then bob should have moderator permissions
    And bob should see moderation tools

  @circle_moderator
  Scenario: Moderator can manage content
    Given I am logged in as bob
    And bob is moderator of circle "Book Club"
    When I view the circle
    Then I should see "🛡️ Moderator" badge
    And I should be able to:
      | action                 |
      | delete_any_post        |
      | pin_post               |
      | remove_member          |
    But I should not be able to:
      | action                 |
      | delete_circle          |
      | change_circle_settings |

  @circle_moderator @security
  Scenario: Moderator cannot promote to owner
    Given I am logged in as bob
    When I try to promote charlie to moderator
    Then I should see "Permission denied"
    And charlie should remain a regular member

  @circle_member
  Scenario: Member can participate
    Given I am logged in as charlie
    And charlie is member of circle "Book Club"
    When I view the circle
    Then I should see "👤 Member" badge
    And I should be able to:
      | action                 |
      | view_posts             |
      | create_post            |
      | comment                |
      | like_posts             |
    But I should not be able to:
      | action                 |
      | delete_others_posts    |
      | remove_members         |
      | access_moderation      |

  @circle_member @security
  Scenario: Member cannot access moderation
    Given I am logged in as charlie
    When I try to access the moderation panel
    Then I should see "You don't have permission"

  @complex
  Scenario: User has different roles in different circles
    Given the following circle memberships exist:
      | user    | circle        | role      |
      | alice   | Book Club     | Owner     |
      | alice   | Gaming        | Member    |
      | bob     | Book Club     | Moderator |
      | bob     | Gaming        | Owner     |
    
    When I login as alice
    And I view circle "Book Club"
    Then I should see "👑 Owner" badge
    
    When I view circle "Gaming"
    Then I should see "👤 Member" badge
    
    When I login as bob
    And I view circle "Book Club"
    Then I should see "🛡️ Moderator" badge
    
    When I view circle "Gaming"
    Then I should see "👑 Owner" badge