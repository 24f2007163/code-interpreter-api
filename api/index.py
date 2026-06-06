from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from io import StringIO
import traceback
import sys
import os
import json
import httpx

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class CodeRequest(BaseModel):
    code: str


def execute_python_code(code: str):

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


async def analyze_error_with_ai(code, tb):

    prompt = f"""
Analyze this Python code and traceback.

CODE:
{code}

TRACEBACK:
{tb}

Return ONLY JSON:

{{"error_lines":[line_numbers]}}
"""

    async with httpx.AsyncClient() as client:

        response = await client.post(
            "https://aipipe.org/openai/v1/chat/completions",
            headers={
                "Authorization":
                f"Bearer {os.environ['AIPIPE_TOKEN']}"
            },
            json={
                "model": "openai/gpt-4.1-nano",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "response_format": {
                    "type": "json_object"
                }
            }
        )

    data = response.json()

    content = (
        data["choices"][0]
        ["message"]["content"]
    )

    try:
        return json.loads(content)["error_lines"]
    except:
        return []


@app.post("/code-interpreter")
async def code_interpreter(req: CodeRequest):

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
