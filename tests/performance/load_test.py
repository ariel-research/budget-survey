import logging
import os
import random
import sys

from locust import HttpUser, task

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))


from app import create_app
from application.services.awareness_check import create_random_vector
from database.queries import get_subjects

logger = logging.getLogger(__name__)


class SurveyUser(HttpUser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = create_app()
        self.app_context = self.app.app_context()

    def on_start(self):
        self.app_context.push()
        self.user_id = random.randint(1, 10000)
        self.survey_id = 1
        self.subjects = get_subjects(self.survey_id)
        logger.info(
            f"Starting new user session with user_id: {self.user_id}, subjects: {self.subjects}"
        )

    def on_stop(self):
        self.app_context.pop()
        total_requests = self.environment.stats.total.num_requests
        total_failures = self.environment.stats.total.num_failures
        logger.info(
            f"Total Requests: {total_requests}, Failed Requests: {total_failures}"
        )

    @task
    def complete_survey(self):
        try:
            # Step 1: Access the index page
            logger.debug(f"User {self.user_id}: Accessing index page")
            with self.client.get(
                f"/?userid={self.user_id}&surveyid={self.survey_id}",
                catch_response=True,
            ) as response:
                if response.status_code != 200:
                    logger.error(
                        f"User {self.user_id}: Failed to access index page. Status code: {response.status_code}"
                    )
                    response.failure("Failed to access index page")
                else:
                    response.success()

            # Step 2: Create vector
            logger.debug(f"User {self.user_id}: Creating vector")
            vector = create_random_vector(len(self.subjects))
            with self.client.post(
                f"/create_vector?userid={self.user_id}&surveyid={self.survey_id}",
                data={subject: value for subject, value in zip(self.subjects, vector)},
                catch_response=True,
                allow_redirects=False,
            ) as response:
                if response.status_code != 302:
                    logger.error(
                        f"User {self.user_id}: Failed to create vector. Status code: {response.status_code}"
                    )
                    response.failure("Failed to create vector")
                else:
                    response.success()

            # Step 3: Complete survey
            logger.debug(f"User {self.user_id}: Accessing survey page")
            vector_str = ",".join(map(str, vector))
            with self.client.get(
                f"/survey?vector={vector_str}&userid={self.user_id}",
                catch_response=True,
            ) as response:
                if response.status_code != 200:
                    logger.error(
                        f"User {self.user_id}: Failed to access survey page. Status code: {response.status_code}"
                    )
                    response.failure("Failed to access survey page")
                else:
                    response.success()

            logger.debug(f"User {self.user_id}: Submitting survey")
            survey_data = {
                "user_vector": vector_str,
                "awareness_check": "2",
            }
            for i in range(10):
                survey_data[f"option1_{i}"] = ",".join(
                    map(str, create_random_vector(len(self.subjects)))
                )
                survey_data[f"option2_{i}"] = ",".join(
                    map(str, create_random_vector(len(self.subjects)))
                )
                survey_data[f"choice_{i}"] = random.choice(["1", "2"])

            with self.client.post(
                f"/survey?userid={self.user_id}",
                data=survey_data,
                catch_response=True,
                allow_redirects=False,
            ) as response:
                if response.status_code not in [200, 302]:
                    logger.error(
                        f"User {self.user_id}: Failed to submit survey. Status code: {response.status_code}"
                    )
                    response.failure("Failed to submit survey")
                else:
                    response.success()

            # Step 4: Thank you page
            logger.debug(f"User {self.user_id}: Accessing thank you page")
            with self.client.get("/thank_you", catch_response=True) as response:
                if response.status_code != 200:
                    logger.error(
                        f"User {self.user_id}: Failed to access thank you page. Status code: {response.status_code}"
                    )
                    response.failure("Failed to access thank you page")
                else:
                    response.success()

            logger.debug(f"User {self.user_id}: Completed survey process successfully")

        except Exception as e:
            logger.error(f"User {self.user_id}: An error occurred: {str(e)}")
