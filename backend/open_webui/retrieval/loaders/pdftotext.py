import logging
import requests
from open_webui.env import SRC_LOG_LEVELS
import time
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])

# Retry até 3 vezes com espera exponencial (1s, 2s, 4s), apenas em falhas de request


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_exception_type(requests.RequestException),
    reraise=True  # lança o erro após esgotar as tentativas
)
def post_with_retry(url, headers=None, files=None, data=None):
    r = requests.post(url=url, headers=headers, files=files, data=data)
    r.raise_for_status()  # Lança um HTTPError se o status não for 2xx
    return r


class PdftotextLoader():
    def __init__(self, pdf_path: str, url: str, max_pages: int):
        self.pdf_path = pdf_path
        url += "/api-ds-ocr/text_extract"
        self.url = url
        self.max_pages = max_pages

    def load(self):
        with open(self.pdf_path, "rb") as f:
            pdf = f.read()

        log.info(self.max_pages)

        headers = {
            "accept": "application/json",
        }

        files = {
            "pdf_upload": pdf
        }
        data = {
            'max_pages': self.max_pages,
            'header_footer': True
        }

        r = requests.post(url=self.url, headers=headers,
                          files=files, data=data, timeout=240)
        log.info(r)

        response = r.json()
        txt = response.get("text", "")

        # log.info(f"REQ_ID: %s Extracted text from pdf using OCR, {txt} -> %s ")

        return txt


class PdftotextLoaderAsync:
    def __init__(self, pdf_path: str, url: str, max_pages: int):
        self.pdf_path = pdf_path
        self.base_url = url + "/api-ds-ocr"
        self.url = self.base_url + "/text_extract_async"
        self.max_pages = max_pages

    def load(self):
        log.info(self.max_pages)

        with open(self.pdf_path, "rb") as f:
            pdf = f.read()

        headers = {
            "accept": "application/json",
        }

        files = {
            "pdf_upload": pdf
        }

        data = {
            'max_pages': self.max_pages,
            'header_footer': True
        }

        r = self.send_pdf_ocr(files, data, headers)

        if r is None:
            log.error("Failed to extract text from PDF using OCR after retries.")
            return None
        log.info(r)
        response = r.json()
        task_id = response.get("task_id", "")

        log.info(
            f"Extracted text from pdf using OCR, task_id -> {task_id} ")

        return task_id

    def send_pdf_ocr(self, files, data, headers):
        try:
            r = post_with_retry(url=self.url, headers=headers,
                                files=files, data=data)
            return r
        except requests.RequestException as e:
            log.error(
                f"Failed to extract text from PDF using OCR after retries: {e}")
            return None

    def check_status(self, task_id):
        """
        Synchronously checks the status of an OCR extraction task.
        """
        status_url = f"{self.base_url}/task_status/{task_id}"

        r = requests.get(url=status_url, timeout=30)

        if r.status_code != 200:
            log.error(
                f"Failed to check status for task {task_id}: {r.status_code} - {r.text}")
            return None

        response = r.json()

        # self.task_cache[task_id] = response.get("status", "unknown")

        return response

    def get_text(self, task_id):
        """
        Synchronously retrieves the extracted text once the task is completed.
        """
        time_to_sleep = 10
        linear_theshold = 100
        linear_limit = 60*5
        start_time = time.time()
        elapsed_time = 0
        while True:
            status_response = self.check_status(task_id)
            if status_response and status_response.get("status") == "completed":
                return status_response.get("result").get('result')
            # Avoids CPU overload by waiting before rechecking
            time.sleep(time_to_sleep)

            elapsed_time = time.time() - start_time
            if elapsed_time > linear_limit:
                raise Exception(
                    f"Timeout waiting for OCR task to complete, elapsed time: {elapsed_time} seconds"
                )

            if time_to_sleep < linear_theshold:
                time_to_sleep *= 2
