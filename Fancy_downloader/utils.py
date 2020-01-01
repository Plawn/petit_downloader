import requests
from typing import Tuple, List, Dict
import time

RETRY_SLEEP_TIME = 0.3
MAX_RETRY = 10

class Action:
    """
    A function to execute, followed by its args
    """

    def __init__(self, func, *args):
        self.function = func
        self.args = [*args]

    def __call__(self): self.function(*self.args)


def get_size(url: str, session: requests.Session = None) -> Tuple[int, requests.Request]:
    requester = session if session is not None else requests
    r = requester.head(url, headers={'Accept-Encoding': 'identity'})
    return (int(r.headers.get('content-length', 0)), r)


def sm_split(sizeInBytes: int, numsplits: int, offset: int = 0) -> List[str]:
    if numsplits <= 1:
        return [f"0-{sizeInBytes}"]
    lst = []
    i = 0
    lst.append('%s-%s' % (i + offset, offset + int(round(1 + i *
                                                         sizeInBytes/(numsplits*1.0) + sizeInBytes/(numsplits*1.0)-1, 0))))
    for i in range(1, numsplits):
        lst.append('%s-%s' % (offset + int(round(1 + i * sizeInBytes/(numsplits*1.0), 1)), offset +
                              int(round(1 + i * sizeInBytes/(numsplits*1.0) + sizeInBytes/(numsplits*1.0)-1, 0))))
    return lst


def extract_int(string: str) -> str:
    return ''.join(i for i in string if i in '0123456789')



def prepare_name(url:str) -> str :
    splited = url.split('/')
    resized = ''
    try:
        resized = splited[-1][:20] + '.' + splited[-1].split('.')[1]
    except:
        resized = splited[-1][:30]
    return resized


def get_and_retry(url, split='', d_obj=None, session: requests.Session = None):
    headers = {
        'Range': f'bytes={split}'
    }
    done = False
    errors = 0
    requester = session if session is not None else requests
    while not done:
        response = requester.get(url, headers=headers, stream=True)
        if response.status_code < 300:
            done = True
            return response
        else:
            errors += 1
            print(f"error retrying | error code {response.status_code}")
            # should be parameters
            time.sleep(RETRY_SLEEP_TIME)
            if errors == MAX_RETRY:
                print('Download canceled')
                d_obj.has_error = True
                d_obj.stop()
                raise Exception("Error max retry")


def get_chunk(url: str, split, d_obj, session: requests.Session = None):
    l = split.split('-')
    response = get_and_retry(url, split, d_obj, session)
    at = int(l[0])
    for data in response.iter_content(chunk_size=d_obj.chunk_size):
        if not d_obj.is_stopped():
            at = d_obj.write_at(at, data)
            if d_obj.is_paused():
                d_obj.event.wait(d_obj.pause_time)
        else:
            return False
    return True