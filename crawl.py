from datetime import timedelta
from time import sleep, time
import pickle
from pathlib import Path
import json
import logging
import bz2
from concurrent.futures import as_completed, ThreadPoolExecutor
import threading
import itertools

from tqdm.auto import tqdm
import requests
from requests.adapters import HTTPAdapter, Retry


API_TOKEN = ''
API_TOKEN_ALT = ''
API_URL = ''


logging.basicConfig(
    filename='hamster.log',
    encoding='utf-8',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'  # Optional: custom date format
)


class GitHubRetry(Retry):
    def increment(self, method, url, response=None, error=None, _pool=None, _stacktrace=None):
        if response and response.status in (403, 429,) and not int(response.headers.get('X-RateLimit-Remaining', 1)) > 0:
            rate_limit_reset = int(
                response.headers.get('X-RateLimit-Reset', 0))
            wait_until_reset = max(0, int(rate_limit_reset - time()) + 1)
            logging.info('[%i] %s hit rate limit; wait %s for reset',
                         response.status, url, timedelta(seconds=wait_until_reset))
            sleep(wait_until_reset)
        return super().increment(method, url, response, error, _pool, _stacktrace)


class GitHubAPIError(Exception):
    pass


class GitHubAPI:

    def __init__(self, api_tokens: list, api_url: str = 'https://api.github.com/', timeout: int = 180, out_dir=Path('./data')):
        if api_url[-1] != '/':
            api_url += '/'
        self.api_url = api_url
        self.timeout = timeout
        self.out_dir = out_dir
        self.session_pool = [GitHubAPI._create_session(
            api_token) for api_token in api_tokens]
        self.session_iterator = itertools.cycle(self.session_pool)
        self.lock = threading.Lock()

    def _get_session(self):
        with self.lock:
            return next(self.session_iterator)

    def _create_session(api_token):
        retries = GitHubRetry(total=8,
                              backoff_factor=2,
                              status_forcelist=(
                                  403, 429, 500, 501, 502, 503, 504,),
                              raise_on_status=False)
        http_session = requests.Session()
        http_session.headers.update({
            'User-Agent': 'hamster_bth',
            'Accept': 'application/vnd.github+json',
            'Authorization': f'Bearer {api_token}',
        })
        http_adapter = HTTPAdapter(max_retries=retries)
        http_session.mount('https://', http_adapter)
        http_session.mount('http://', http_adapter)
        return http_session

    def query_endpoint(self, endpoint: str, params: dict = {}, use_cache=True, paginate=True):
        path = self.out_dir/Path(endpoint + '.json.bz2')
        if path.exists() and use_cache:
            with open(path, 'rb') as file:
                byte_data = bz2.decompress(file.read())
                return json.loads(byte_data)
        else:
            result = {}
            session = self._get_session()
            response = session.get(
                self.api_url + endpoint, timeout=self.timeout, params=params)
            if response.status_code != 200:
                raise GitHubAPIError(
                    f'[{response.status_code}] for {response.url}: {response.text}')

            result = response.json()

            while 'next' in response.links and paginate:
                next_url = response.links['next']['url']
                response = session.get(next_url, timeout=self.timeout)
                if response.status_code != 200:
                    raise GitHubAPIError(
                        f'[{response.status_code}] for {response.url}: {response.text}')
                result += response.json()

            path.parent.mkdir(parents=True, exist_ok=True)
            byte_data = json.dumps(result).encode()
            compressed_byte_data = bz2.compress(byte_data)
            with open(path, 'wb') as file:
                file.write(compressed_byte_data)

            return result

    def query_endpoints(self, endpoints, params={}, use_cache=True):
        results = {}
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(
                self.query_endpoint, endpoint, params, use_cache): endpoint for endpoint in endpoints}
            for future in tqdm(as_completed(futures), total=len(futures)):
                endpoint = futures[future]
                try:
                    results[endpoint] = future.result()
                except Exception as e:
                    logging.warning(f'{e} for endpoint {endpoint}')
        return results


gh = GitHubAPI([API_TOKEN, API_TOKEN_ALT], API_URL)
organizations = gh.query_endpoint('organizations', params={'per_page': 100})
repo_endpoints = [
    f'orgs/{organization['login']}/repos' for organization in organizations]


repos = gh.query_endpoints(repo_endpoints, params={
                           'type': 'all', 'per_page': 100})


pull_end_points = ['repos/' + repo['full_name'] +
                   '/pulls' for repo in itertools.chain.from_iterable(repos.values())]


pulls = gh.query_endpoints(pull_end_points, params={
                           'state': 'all', 'per_page': 100})


with open('pulls.pickle', 'wb') as handle:
    pickle.dump(pulls, handle, protocol=pickle.HIGHEST_PROTOCOL)

with open('pulls.pickle', 'rb') as handle:
    pulls = pickle.load(handle)


timeline_endpoints = []
for owner, name, pull_number in tqdm(pulls):
    endpoint = f'repos/{owner}/{name}/issues/{pull_number}/timeline'
    path = gh.out_dir/Path(endpoint + '.json')
    if not path.exists():
        timeline_endpoints += [endpoint]
    else:
        with open(path, 'rb') as file:
            byte_data = file.read()
        new_path = gh.out_dir/Path(endpoint + '.json.bz2')
        compressed_byte_data = bz2.compress(byte_data)
        with open(new_path, 'wb') as file:
            file.write(compressed_byte_data)
        path.unlink()


with open('timelines.pickle', 'wb') as handle:
    pickle.dump(timeline_endpoints, handle, protocol=pickle.HIGHEST_PROTOCOL)
