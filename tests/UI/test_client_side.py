from urllib.parse import parse_qs, urlparse

import pytest


class MockElement:
    """Mocks a DOM element."""

    def __init__(self, element_type, value=None):
        self.element_type = element_type
        self.value = value


class MockDriver:
    """Mocks a web driver for testing purposes."""

    def __init__(self):
        self.current_url = ""
        self.elements = {}
        self.form_data = {}

    def get(self, url):
        """Simulates navigating to a URL."""
        self.current_url = url
        if "create_vector" in url:
            self.elements["select"] = [MockElement("select") for _ in range(3)]
        elif "survey" in url:
            self.elements[".pair-container"] = [MockElement("div") for _ in range(5)]
            self.elements["awareness_check"] = MockElement("input", "2")
            self.elements["submit"] = MockElement("button")

    def find_element(self, by, value):
        """Simulates finding a single element on the page."""
        if "awareness_check" in value:
            return self.elements.get("awareness_check", MockElement("input"))
        elif "submit-container" in value:
            return self.elements.get("submit", MockElement("button"))
        return MockElement("input")

    def find_elements(self, by, value):
        """Simulates finding multiple elements on the page."""
        return self.elements.get(value, [])

    def submit_form(self):
        """Simulates form submission and potential redirection."""
        if "survey" in self.current_url:
            if (
                all(self.form_data.get(f"choice_{i}") for i in range(10))
                and self.form_data.get("awareness_check") == "2"
            ):
                self.current_url = self.current_url.replace("survey", "thank_you")


@pytest.fixture
def mock_driver():
    """Provides a mock driver instance for each test."""
    return MockDriver()


@pytest.fixture
def base_url():
    """Provides the base URL for the application under test."""
    return "http://localhost:5001"


def test_index_page(mock_driver, base_url):
    """Test if the index page loads correctly with proper query parameters."""
    mock_driver.get(f"{base_url}/?userid=123&surveyid=1")
    parsed_url = urlparse(mock_driver.current_url)
    query_params = parse_qs(parsed_url.query)

    assert parsed_url.path == "/"
    assert query_params.get("userid") == ["123"]
    assert query_params.get("surveyid") == ["1"]


def test_create_vector_page(mock_driver, base_url):
    """Test if the create vector page loads and processes form submission."""
    mock_driver.get(f"{base_url}/create_vector?userid=123&surveyid=1")
    parsed_url = urlparse(mock_driver.current_url)

    assert parsed_url.path == "/create_vector"

    selects = mock_driver.find_elements(None, "select")
    assert len(selects) == 3


def test_survey_page(mock_driver, base_url):
    """Test if the survey page loads, processes user input, and redirects correctly."""
    mock_driver.get(f"{base_url}/survey?userid=123&vector=25,25,50")
    parsed_url = urlparse(mock_driver.current_url)
    query_params = parse_qs(parsed_url.query)

    assert parsed_url.path == "/survey"
    assert query_params.get("userid") == ["123"]
    assert query_params.get("vector") == ["25,25,50"]

    comparison_pairs = mock_driver.find_elements(None, ".pair-container")
    assert len(comparison_pairs) > 0

    for i in range(10):
        mock_driver.form_data[f"choice_{i}"] = "1"

    mock_driver.form_data["awareness_check"] = "2"

    mock_driver.submit_form()

    assert "/thank_you" in mock_driver.current_url


def test_thank_you_page(mock_driver, base_url):
    """Test if the thank you page loads correctly."""
    mock_driver.get(f"{base_url}/thank_you")
    parsed_url = urlparse(mock_driver.current_url)

    assert parsed_url.path == "/thank_you"
