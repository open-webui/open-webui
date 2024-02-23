from bs4 import BeautifulSoup
import json
import markdown
import time


from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi import HTTPException
from fastapi.middleware.wsgi import WSGIMiddleware
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException


from apps.ollama.main import app as ollama_app
from apps.openai.main import app as openai_app
from apps.audio.main import app as audio_app
from apps.images.main import app as images_app
from apps.rag.main import app as rag_app

from apps.web.main import app as webui_app

from config import ENV, VERSION, FRONTEND_BUILD_DIR


class SPAStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except (HTTPException, StarletteHTTPException) as ex:
            if ex.status_code == 404:
                return await super().get_response("index.html", scope)
            else:
                raise ex


app = FastAPI(docs_url="/docs" if ENV == "dev" else None, redoc_url=None)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def check_url(request: Request, call_next):
    start_time = int(time.time())
    response = await call_next(request)
    process_time = int(time.time()) - start_time
    response.headers["X-Process-Time"] = str(process_time)

    return response


app.mount("/api/v1", webui_app)

app.mount("/ollama/api", ollama_app)
app.mount("/openai/api", openai_app)

app.mount("/images/api/v1", images_app)
app.mount("/audio/api/v1", audio_app)
app.mount("/rag/api/v1", rag_app)


@app.get("/api/config")
async def get_app_config():

    return {
        "status": True,
        "version": VERSION,
        "images": images_app.state.ENABLED,
        "default_models": webui_app.state.DEFAULT_MODELS,
        "default_prompt_suggestions": webui_app.state.DEFAULT_PROMPT_SUGGESTIONS,
    }


# Function to parse each section
def parse_section(section):
    items = []
    for li in section.find_all("li"):
        # Extract raw HTML string
        raw_html = str(li)

        # Extract text without HTML tags
        text = li.get_text(separator=" ", strip=True)

        # Split into title and content
        parts = text.split(": ", 1)
        title = parts[0].strip() if len(parts) > 1 else ""
        content = parts[1].strip() if len(parts) > 1 else text

        items.append({"title": title, "content": content, "raw": raw_html})
    return items


@app.get("/api/changelog")
async def get_app_changelog():
    try:
        with open("../CHANGELOG.md", "r") as file:
            changelog_content = file.read()
        # Convert markdown content to HTML
        html_content = markdown.markdown(changelog_content)

        # Parse the HTML content
        soup = BeautifulSoup(html_content, "html.parser")

        print(soup)
        # Initialize JSON structure
        changelog_json = {}

        # Iterate over each version
        for version in soup.find_all("h2"):
            version_number = (
                version.get_text().strip().split(" - ")[0][1:-1]
            )  # Remove brackets
            date = version.get_text().strip().split(" - ")[1]

            version_data = {"date": date}

            # Find the next sibling that is a h3 tag (section title)
            current = version.find_next_sibling()

            print(current)

            while current and current.name != "h2":
                if current.name == "h3":
                    section_title = current.get_text().lower()  # e.g., "added", "fixed"
                    section_items = parse_section(current.find_next_sibling("ul"))
                    version_data[section_title] = section_items

                # Move to the next element
                current = current.find_next_sibling()

            changelog_json[version_number] = version_data

        # print(changelog_json)

        # Return content as JSON string
        return changelog_json
    except FileNotFoundError:
        return {"error": "readme.md not found"}
    except Exception as e:
        return {"error": f"An error occurred: {e}"}


app.mount(
    "/",
    SPAStaticFiles(directory=FRONTEND_BUILD_DIR, html=True),
    name="spa-static-files",
)
