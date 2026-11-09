"""Public generic scheduler: never stores private code, data, or models in GitHub."""
import json
import hashlib
import hmac
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import urllib.request
import venv


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, new_url):
        return None


def collection_outcome(result):
    if not isinstance(result, dict):
        raise RuntimeError('Invalid collection response')
    data = result.get("data") if isinstance(result, dict) else None
    status = data.get("status") if isinstance(data, dict) else None
    if result.get("error") or result.get("ok") is False or status not in {"ok", "partial", "busy"}:
        raise RuntimeError("Collection did not complete")
    return {"ok": "updated", "partial": "partial", "busy": "busy"}[status]


def bundle_files(bundle):
    if not isinstance(bundle, dict) or bundle.get('schemaVersion') != 1:
        raise ValueError('Invalid private trainer schema')
    files = bundle.get('files', {})
    if not isinstance(files, dict) or set(files) != {'run.py', 'requirements.txt'} or not all(isinstance(text, str) for text in files.values()):
        raise ValueError('Invalid private trainer files')
    expected = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
    if not isinstance(bundle.get('sha256'), str) or not hmac.compare_digest(expected, bundle['sha256']):
        raise ValueError('Private trainer integrity check failed')
    return files


def invoke(path, payload=None):
    origin = os.environ["SITE_URL"].rstrip("/")
    if not origin.startswith("https://"):
        raise ValueError("HTTPS Site origin is required")
    headers = {"OAI-Sites-Authorization": "Bearer " + os.environ["SITE_ACCESS_TOKEN"],
               "Authorization": "Bearer " + os.environ["JOB_TOKEN"], "Content-Type": "application/json",
               "X-Runner-Repository": os.environ.get("GITHUB_REPOSITORY", "")}
    request = urllib.request.Request(origin + path, headers=headers,
                                     data=None if payload is None else json.dumps(payload).encode())
    # An expired Site token can redirect to sign-in. Never forward either secret.
    with urllib.request.build_opener(NoRedirect()).open(request, timeout=180) as response:
        return json.loads(response.read(4 * 1024 * 1024))


def main():
    if os.environ.get("RUN_ACTION", "collect") == "collect":
        result = invoke("/api/jobs/collect", {})
        outcome = collection_outcome(result)
        print({"updated": "Private collection completed.", "partial": "Private collection completed with some upstream sources unavailable.", "busy": "Collection skipped because another cloud run is in progress."}[outcome])
        return
    bundle = invoke("/api/jobs/training/bundle")
    files = bundle_files(bundle)
    with tempfile.TemporaryDirectory(prefix="private-cloud-training-") as directory:
        root = Path(directory)
        for name, contents in files.items():
            if not isinstance(contents, str):
                raise ValueError("Invalid private trainer content")
            (root / name).write_text(contents)
        venv.EnvBuilder(with_pip=True).create(root / "venv")
        python = root / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        subprocess.run([str(python), "-m", "pip", "install", "--disable-pip-version-check", "--no-cache-dir", "-r", str(root / "requirements.txt")], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)
        subprocess.run([str(python), str(root / "run.py")], check=True, timeout=6600)
    print("Private cloud training completed.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("Cloud job failed safely:", type(error).__name__, file=sys.stderr)
        raise SystemExit(1)
