'''Expand a dict into a collection of subdirectories and json files or
   contract (un-expand) the output of expand() into a dict.

    Construct

      expandomatic = JsonExpandOMatic(path=data_path, logger=logger)

    Expand

      data = { ... }

      data_path = sys.argv[1] if len(sys.argv) > 1 else '.'

      expandomatic.expand(data)
        Creates {data_path}/root.json and {data_path}/root/...

      expandomatic.expand(foo, root_element='foo')
        Creates {data_path}/foo.json and {data_path}/foo/...

      Warning: expand() is destructive unless `preserve=True`

    Contract

      data = expandomatic.contract()

      import jsonref
      with open(f'{data_path}/root.json') as f:
        data = jsonref.load(f, base_uri=f'file://{os.path.abspath(data_path)}/')


'''

import json
import logging
import os
from urllib.parse import urlparse

import concurrent.futures
import threading
import time
from queue import Queue, Empty

class JsonExpandOMatic:

  def __init__(self, *, path, logger=logging.getLogger(__name__)):
    self.path = os.path.abspath(path)
    self.logger = logger
    self.progress_level = 0
    self.populate_delay = 10.0
    self.drain_wait = 10.0

  def expand(self, data, root_element='root', preserve=True):
    '''Expand a dict into a collection of subdirectories and json files.

        Creates:
        - {self.path}/{root_element}.json
        - {self.path}/{root_element}/...
    '''
    if preserve:
      data = json.loads(json.dumps(data))
    return self._expand(path=self.path, key=root_element,
                        data={root_element: data}, ref='.')

  def contract(self, root_element='root'):
    '''Contract (un-expand) the results of `expand()` into a dict.

        Loads:
        - {self.path}/{root_element}.json
        - {self.path}/{root_element}/...
    '''

    self.queue = Queue()
    self.event = threading.Event()

    def _delegate(*args, **kwargs):
        self._dequeue_contract_recursion(*args, **kwargs)

    with concurrent.futures.ThreadPoolExecutor() as executor:
      workers = executor._max_workers - 1
      self.logger.debug(f"executor._max_workers = {executor._max_workers}")
      while workers:
          executor.submit(_delegate, workers)
          workers -= 1

      self.logger.info("Main: Ready to work")

      r = self._contract(
          path=[self.path],
          data=self._slurp(self.path, f"{root_element}.json"))

      self.logger.info("Main: Waiting for queue to populate.")
      time.sleep(self.populate_delay)

      self.logger.info(f"Main: Waiting for queue to drain. (size={self.queue.qsize()})")
      while not self.queue.empty():
        self.logger.info(f"Main: Queue is processing. (size={self.queue.qsize()})")
        time.sleep(self.drain_wait)

      self.logger.info(f"Main: Queue is empty. (size={self.queue.qsize()})")
      self.event.set()

      self.logger.info("Main: Done")

      return r

  def _expand(self, *, path, key, data, ref, indent=0):
    self.logger.debug(' ' * indent + f"path [{path}] key [{key}] ref [{ref}]")

    if not isinstance(data, dict) and not isinstance(data, list):
      return data

    if not isinstance(data[key], dict) and not isinstance(data[key], list):
      return data

    if not data[key]:
      self.logger.debug(' ' * indent + f"data[{key}] is falsy")
      return data

    if not os.path.exists(path):
      os.mkdir(path)

    # FIXME: Do this with a regex
    filename_key = str(key).replace(':', '_').replace('/', '_').replace('\\', '_')

    if isinstance(data[key], list):
      self.logger.debug(' ' * indent + '>> IS A LIST <<')
      for k, v in enumerate(data[key]):
        self._expand(path=os.path.join(path, str(filename_key)),
                     key=k, data=data[key], ref=f"{ref}/{key}",
                     indent=indent + 2)

    elif isinstance(data[key], dict):
      self.logger.debug(' ' * indent + '>> IS A DICT <<')

      keys = sorted(data[key].keys())
      for k in keys:
        # v = data[key][k]
        self.logger.debug(' ' * indent + k)
        self._expand(path=os.path.join(path, str(filename_key)),
                     key=k, data=data[key], ref=key,
                     indent=indent + 2)

      with open(f"{path}/{filename_key}.json", 'w') as f:
        json.dump(data[key], f, indent=4, sort_keys=True)

      data[key] = {'$ref': f"{ref}/{filename_key}.json"}

    try:
      os.rmdir(path)
    except Exception:
      pass

    return data

  def _contract(self, *, path, data, depth=0):

    if depth < self.progress_level:
      self.logger.info(f"{'  '*depth}>>>{path}")
    elif depth:
      self.logger.debug(f"{'  '*depth}>>>{path}")

    if isinstance(data, list):
      for k, v in enumerate(data):
        self._queue_contract_recursion(depth=depth+1,
          recursion={'path':path, 'data':v}, target={'data':data, 'key':k})
        # data[k] = self._contract(depth=depth+1, path=path, data=v)

    elif isinstance(data, dict):

      for k, v in data.items():
        if self._something_to_follow(k,v):
          data = self._contract(depth=depth+1,
                                path=path + [os.path.dirname(v)],
                                data=self._slurp(*path, v))
          break
        else:
          self._queue_contract_recursion(depth=depth+1,
            recursion={'path':path, 'data':v}, target={'data':data, 'key':k})
          # data[k] = self._contract(depth=depth+1, path=path, data=v)

    if depth < self.progress_level:
      self.logger.info(f"{'  '*depth}<<<{path}")
    elif depth:
      self.logger.debug(f"{'  '*depth}<<<{path}")

    return data

  def _dequeue_contract_recursion(self, cid):
    self.logger.debug(f"Started consumer {cid}")
    while not self.event.is_set():
      try:
        depth, recursion, target = self.queue.get(block=True, timeout=1)
        key = target['key']
        target['data'][key] = self._contract(depth=depth, path=recursion['path'], data=recursion['data'])
      except Empty as e:
        self.logger.debug(f"{cid} -- {e}")
        pass
    self.logger.debug(f"Stopping consumer {cid}")

  def _queue_contract_recursion(self, *, depth, recursion, target):
    # key = target['key']
    # target['data'][key] = self._contract(depth=depth, path=recursion['path'], data=recursion['data'])
    self.queue.put((depth, recursion, target))

  def _slurp(self, *args):
    with open(os.path.join(*args)) as f:
      return json.load(f)

  def _something_to_follow(self, k, v):

    if k != '$ref':
      return False

    url_details = urlparse(v)
    return not (url_details.scheme or url_details.fragment)
