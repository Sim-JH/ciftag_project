import ciftag.utils.logger as logger
from ciftag.services.flickr import login, search

from playwright.sync_api import sync_playwright


logs = logger.Logger(log_dir='test')

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()

    result = login.login(
        logs, context, 0, 'saide0032@gmail.com', '!anr@rlgmr0032'
    )

    search.search(
        logs, 0, result['page'], 'test', ['girl', 'bikini'], 5
    )
