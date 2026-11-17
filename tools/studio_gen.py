"""Call Unsloth Studio's generate_image with a deadline (Studio generations have hung for hours).

    python3 -I tools/studio_gen.py args.json out.png [--timeout 180]

args.json holds generate_image's arguments (prompt, init_image {"path": ...}, mask_image,
strength, steps, seed, width, height, workflow, reference_images...). The image is saved
to out.png. On timeout the generation is cancelled and the script exits 2. Auth comes
from the same headersHelper as the MCP server; the key is never printed.
"""
import json
import os
import signal
import subprocess
import sys
import urllib.request

URL = "http://127.0.0.1:8888/mcp/"
HELPER = os.path.expanduser("~/.claude/mcp-headers/unsloth-studio.sh")


class Client:
    def __init__(self):
        self.headers = json.loads(subprocess.check_output([HELPER]))
        self.headers.update({"Content-Type": "application/json", "Accept": "application/json, text/event-stream"})
        self.n = 0
        r = self.rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                    "clientInfo": {"name": "studio_gen", "version": "1"}}, 30)
        self.rpc("notifications/initialized", None, 30, notify=True)

    def rpc(self, method, params, timeout, notify=False):
        body = {"jsonrpc": "2.0", "method": method}
        if params is not None: body["params"] = params
        if not notify:
            self.n += 1
            body["id"] = self.n
        req = urllib.request.Request(URL, json.dumps(body).encode(), self.headers)
        with urllib.request.urlopen(req, timeout=timeout) as res:
            sid = res.headers.get("Mcp-Session-Id")
            if sid: self.headers["Mcp-Session-Id"] = sid
            text = res.read().decode()
        if notify or not text.strip(): return None
        # plain JSON, or an SSE stream whose last data line is the result
        if text.lstrip().startswith("{"): msg = json.loads(text)
        else: msg = json.loads([l[5:] for l in text.splitlines() if l.startswith("data:")][-1])
        if "error" in msg: raise RuntimeError(msg["error"])
        return msg["result"]

    def tool(self, name, args, timeout):
        return self.rpc("tools/call", {"name": name, "arguments": args}, timeout)


def main():
    args = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    timeout = float(sys.argv[sys.argv.index("--timeout") + 1]) if "--timeout" in sys.argv else 180
    args.setdefault("return_media", "link")
    c = Client()

    # Studio streams progress every 2 s, so a socket timeout never fires: use a hard deadline.
    def expire(*_): raise TimeoutError("deadline")
    signal.signal(signal.SIGALRM, expire)
    signal.alarm(int(timeout))
    try:
        r = c.tool("generate_image", args, timeout)
        signal.alarm(0)
    except (TimeoutError, OSError) as e:
        signal.alarm(0)
        print(f"timed out after {timeout:.0f}s ({e}); cancelling", file=sys.stderr)
        try: print(Client().tool("cancel", {"kind": "image"}, 30)["content"][0]["text"], file=sys.stderr)
        except Exception as e2: print("cancel failed:", e2, file=sys.stderr)
        sys.exit(2)
    texts = [x["text"] for x in r.get("content", []) if x.get("type") == "text"]
    if r.get("isError"): sys.exit("studio: " + " ".join(texts))
    info = next(json.loads(t) for t in texts if t.lstrip().startswith("{"))
    for i, im in enumerate(info["images"]):
        path = out if len(info["images"]) == 1 else out.replace(".png", f"-{i}.png")
        urllib.request.urlretrieve(im["download_url"], path)
        print(path, im["id"], im.get("seed"))


if __name__ == "__main__":
    main()
