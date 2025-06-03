#### Idealista bot

A telegram chat bot for searching flats in Lisbon at the site idealista.pt within a configurable range of parameters. 

#### Filters

The following filters can be configured from the bot:

- number of rooms with a lower limit (like 1+, 2+ etc.)
- space in sq m (30+, 40+, etc. until 150+)
- city or a custom polygon copypasted from the idealista website
- price range (max)
- furniture present or not
- state of the flat (good, needs remodeling, new)

#### Scraping requirements

There is a set frequency of updates in the bot so that idealista doesn't ban it for too many requests.

#### Testing requirements

Tests should check the following:

1. the ability to scrape website without "too many requests" error
2. the ability to send messages to the bot
3. the ability to receive input from the bot
4. the correct processing of seen listings (not sending them into the chat)
5. the correct saving of user filters
6. the correct changing of user filters
7. that the "back" button works


#### The navigation flow

The main filter configuring flow goes as:

Main Menu -> Filter Menu -> Setting Menu -> Setting Value -> Setting Menu -> Back to Filter Menu
