import urllib.request
import urllib.error
import time

def test_url(url):
    print(f"Testing {url} ...")
    req = urllib.request.Request(url)
    try:
        resp = urllib.request.urlopen(req)
        print(f"Success! Code: {resp.getcode()}")
    except urllib.error.HTTPError as e:
        print(f"HTTPError: {e.code}")
    except Exception as e:
        print(f"Exception: {e}")

test_url('https://sif-sentinel-backend-gu7a.onrender.com/')
test_url('https://sif-sentinel-backend-gu7a.onrender.com/health')
test_url('https://sif-sentinel-backend-gu7a.onrender.com/api/v1/dashboard-summary')
