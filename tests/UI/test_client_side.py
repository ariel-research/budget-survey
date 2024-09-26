import unittest

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


class BudgetSurveyTest(unittest.TestCase):
    def setUp(self):
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service)
        self.driver.implicitly_wait(10)
        self.base_url = "http://localhost:5001"

    def tearDown(self):
        if self.driver:
            self.driver.quit()

    def test_index_page(self):
        self.driver.get(f"{self.base_url}/?userid=123&surveyid=1")

        # Wait for either the welcome message or the thank you message
        try:
            element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "h1"))
            )
            header_text = element.text

            if "ברוכים הבאים לסקר" in header_text:
                start_button = self.driver.find_element(By.CSS_SELECTOR, ".btn")
                self.assertTrue(start_button.is_displayed())
            elif "תודה רבה" in header_text:
                self.assertIn("תודה רבה", self.driver.title)
            else:
                self.fail(f"Unexpected page content: {header_text}")
        except TimeoutException:
            self.fail("Timed out waiting for page to load")

    def test_create_vector_page(self):
        self.driver.get(f"{self.base_url}/create_vector?userid=123&surveyid=1")
        self.assertIn("יצירת וקטור תקציב", self.driver.title)

        selects = self.driver.find_elements(By.TAG_NAME, "select")
        for select in selects[:-1]:
            Select(select).select_by_value("25")
        Select(selects[-1]).select_by_value("50")

        total = self.driver.find_element(By.ID, "total")
        self.assertEqual(total.text, "100")

        submit_button = self.driver.find_element(
            By.CSS_SELECTOR, ".submit-container button"
        )
        submit_button.click()

        WebDriverWait(self.driver, 10).until(EC.url_contains("/survey"))

    def test_survey_page(self):
        self.driver.get(f"{self.base_url}/survey?userid=123&vector=25,25,50")

        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "pair-container"))
            )
        except TimeoutException:
            self.fail("Comparison pairs did not load within the expected time")

        comparison_pairs = self.driver.find_elements(By.CLASS_NAME, "pair-container")
        self.assertGreater(len(comparison_pairs), 0)

        for pair in comparison_pairs:
            try:
                option = pair.find_element(
                    By.CSS_SELECTOR, "input[type='radio'][value='1']"
                )
                option.click()
            except NoSuchElementException:
                self.fail(f"Could not find radio button in pair: {pair.text}")

        try:
            awareness_check = self.driver.find_element(
                By.CSS_SELECTOR, "input[name='awareness_check'][value='2']"
            )
            awareness_check.click()
        except NoSuchElementException:
            self.fail("Could not find awareness check radio button")

        submit_button = self.driver.find_element(
            By.CSS_SELECTOR, ".submit-container button"
        )
        submit_button.click()

        try:
            WebDriverWait(self.driver, 10).until(EC.url_contains("/thank_you"))
        except TimeoutException:
            self.fail("Did not redirect to thank you page after survey submission")

    def test_thank_you_page(self):
        self.driver.get(f"{self.base_url}/thank_you")
        self.assertIn("תודה רבה", self.driver.title)
        thank_you_message = self.driver.find_element(By.TAG_NAME, "h1")
        self.assertIn("תודה רבה", thank_you_message.text)


if __name__ == "__main__":
    unittest.main()
