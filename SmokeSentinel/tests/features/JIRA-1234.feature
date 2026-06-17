Feature: Online Shopping Cart Management
  To provide a seamless and efficient shopping experience by managing items in an online cart effectively, ensuring that users can add products to their carts without errors or issues.

  @smoke @shopping_cart @happy_path
  Scenario: Adding Items Successfully to the Cart
    Given I have navigated to a product page on the website
    And there are no items in my shopping cart currently
    When I add multiple products of different categories into my cart by clicking 'Add to Cart' button for each item individually
    Then all added items should appear in my shopping cart and be correctly assigned with their respective quantities, prices, and images.
    And the total price displayed on the screen after adding these items should match the sum calculated from individual product costs including taxes if applicable.

  @smoke @shopping_cart @error
  Scenario: Adding Items to Cart Fails Due to Insufficient Stock
    Given I have navigated to a popular item that is currently out of stock on the website
    When I attempt to add this product into my shopping cart by clicking 'Add to Cart' button for it individually, multiple times if necessary
    Then an error message should appear indicating insufficient stock and preventing me from adding these items to my cart.

  @smoke @shopping @error
  Scenario: Attempted End Session with Items in the Cart Fails Due to Unfinished Checkout Process
    Given I have added a few products into my shopping cart and navigated back from checkout page without completing it
    When I attempt to log out or navigate away during this unfinished process by clicking 'End Sesssion' button on the top right corner of the screen, multiple times if necessary
    Then an error message should appear indicating that items in my cart are not saved and prompting me to complete checkout before logging out.
