# api/index.py

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from io import StringIO
import traceback
import sys
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    expose_headers=["Access-Control-Allow-Origin"],
)


class CodeRequest(BaseModel):
    code: str


def execute_python_code(code: str):
    """
    Execute Python code and return exact output.
    """

    old_stdout = sys.stdout
    sys.stdout = StringIO()

    try:
        exec(code)

        output = sys.stdout.getvalue()

        return {
            "success": True,
            "output": output
        }

    except Exception:

        output = traceback.format_exc()

        return {
            "success": False,
            "output": output
        }

    finally:
        sys.stdout = old_stdout


async def analyze_error_with_ai(code: str, tb: str):
    """
    Extract line numbers from traceback.
    More reliable than calling an LLM on Vercel.
    """

    matches = re.findall(r'line (\d+)', tb)

    if matches:
        return [int(matches[-1])]

    return []


@app.get("/")
def home():
    return {"status": "ok"}


@app.options("/{path:path}")
def options_handler(path: str):
    return Response()


@app.post("/code-interpreter")
async def code_interpreter(req: CodeRequest):

    try:

        execution = execute_python_code(req.code)

        if execution["success"]:
            return {
                "error": [],
                "result": execution["output"]
            }

        lines = await analyze_error_with_ai(
            req.code,
            execution["output"]
        )

        return {
            "error": lines,
            "result": execution["output"]
        }

    except Exception as e:

        return {
            "error": [],
            "result": str(e)
        }
