import urllib.parse as urlparse

import urllib
import json

from flask import Flask, Blueprint, request, Response, url_for
from werkzeug.datastructures import Headers
from werkzeug.exceptions import NotFound
from yarl import URL
from katyusha_cat.broswer import Browser, Page
import asyncio
from typing import Dict, List

DEFAULT_HOST = "127.0.0.1:8080"
_CACHE = dict()

loop = asyncio.get_event_loop()
app = Flask(__name__)


proxy = Blueprint("proxy", __name__)


class KatyushaSpiderProxy:
    def __init__(self):
        self.chrome = Browser()

    async def open_browser(self):
        if "browser" not in self.__dict__:
            self.browser = await self.chrome._init_browser()

    async def close_browser(self):
        await self.chrome._close_browser()

    async def do_request(self, base_http: Dict):
        page = Page(browser=self.browser, base_http=base_http)
        await page._init_page()
        resp = await page.fetch()
        text = await resp.text()
        headers = resp.headers
        status = resp.status
        await page._close_page()
        return {"text": text, "headers": headers, "status": status}


class Handler:
    def __init__(self):
        pass

    @classmethod
    def headers(cls, request: request) -> Dict:
        request_headers = dict(request.headers)
        if request_headers.get("Host", None) == DEFAULT_HOST:
            request_headers.pop("Host")
        return request_headers

    @classmethod
    def form_data(cls, request: request) -> str:
        request_form = list()
        for k, v in request.form.items():
            request_form.append((k.encode("utf8"), v.encode("utf8")))
        return urllib.parse.urlencode(request_form)


@proxy.route("/proxy/<path:host>/", methods=["GET", "POST", "PUT", "DELETE"])
def proxy_request(host, **kwargs):
    args = dict(request.args)
    url = URL(host).with_query(urllib.parse.urlencode(args))
    scheme = url.scheme
    hostname = url.host
    path = url.path
    query_string = url.query_string or None
    port = url.port
    method = request.method
    request_headers = Handler.headers(request)

    if method in ["POST", "PUT"]:
        form_data = Handler.form_data(request)
        request_headers["Content-Length"] = len(form_data)
    else:
        form_data = None

    if not ("host" in request_headers.keys()):
        request_headers["host"] = hostname

    # if target is for HTTP, use HTTPConnection method.
    item = {
        "url": str(url),
        "method": method,
        "form_data": form_data,
        "headers": request_headers,
        "query_string": query_string,
        "path": path,
    }
    katyusha_spider_proxy = _CACHE.get("KatyushaSpiderProxy")
    resp = loop.run_until_complete(katyusha_spider_proxy.do_request(item))

    # Clean up response headers for forwarding
    d = {}
    response_headers = Headers()
    for key, value in resp.get("headers").items():
        d[key.lower()] = value
        if key in ["content-length", "connection", "content-type"]:
            continue

        if key == "set-cookie":
            cookies = value.split(",")
            [response_headers.add(key, c) for c in cookies]
        else:
            response_headers.add(key, value)

    # If this is a redirect, munge the Location URL
    if "location" in response_headers:
        redirect = response_headers["location"]
        parsed = urlparse.urlparse(request.url)
        redirect_parsed = urlparse.urlparse(redirect)

        redirect_host = redirect_parsed.netloc
        if not redirect_host:
            redirect_host = "%s:%d" % (hostname, port)

        redirect_path = redirect_parsed.path
        if redirect_parsed.query:
            redirect_path += "?" + redirect_parsed.query

        munged_path = url_for(
            ".proxy_request", proto=scheme, host=redirect_host, file=redirect_path[1:]
        )

        url = "%s://%s%s" % (parsed.scheme, parsed.netloc, munged_path)
        response_headers["location"] = url

    # Rewrite URLs in the content to point to our URL schemt.method == " instead.
    # Ugly, but seems to mostly work.
    root = url_for(".proxy_request", proto=scheme, host=host)
    contents = resp.get("text")
    status = resp.get("status")

    # Restructing Contents.
    if "content-type" in d.keys():
        if d["content-type"].find("application/json") >= 0:
            # JSON format conentens will be modified here.
            jc = json.loads(contents)
            if jc.has_key("nodes"):
                del jc["nodes"]
            contents = json.dumps(jc)
    else:
        # set default content-type, for error handling
        d["content-type"] = "text/html; charset=utf-8"

    # Remove transfer-encoding: chunked header. cuz proxy does not use chunk trnasfer.
    if "transfer-encoding" in d:
        if d["transfer-encoding"].lower() == "chunked":
            del d["transfer-encoding"]
            d["content-length"] = len(contents)

    flask_response = Response(response=contents, status=status, headers=d)
    return flask_response


if __name__ == "__main__":
    katyusha_spider_proxy = KatyushaSpiderProxy()
    loop.run_until_complete(katyusha_spider_proxy.open_browser())
    _CACHE.update({"KatyushaSpiderProxy": katyusha_spider_proxy})

    app.register_blueprint(proxy)

    app.run(debug=True, host="127.0.0.1", port=8080)

