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
from queue import Queue


class JsonExpandOMatic:

  def __init__(self, *, path, logger=logging.getLogger(__name__)):
    self.path = os.path.abspath(path)
    self.logger = logger

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
        self._consumer(*args, **kwargs)

    with concurrent.futures.ThreadPoolExecutor() as executor:
      workers = executor._max_workers - 1
      print(f"executor._max_workers = {executor._max_workers}")
      while workers:
          executor.submit(_delegate, workers)
          workers -= 1

      print("Ready to work")

      r = self._contract(
          path=[self.path],
          data=self._slurp(self.path, f"{root_element}.json"))

      print("Main: Waiting for queue to drain.")

      while not self.queue.empty():
        print(f"Main: size={self.queue.qsize()}")
        time.sleep(10.0)

      print(f"Main: size={self.queue.qsize()}")
      print("Main: about to set event.")
      self.event.set()

      print("")

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

    if isinstance(data, list):
      for k, v in enumerate(data):
        self._process(recursion={'path':path, 'data':v}, target={'key':k,'data':v}, depth = depth+1)

    elif isinstance(data, dict):

      for k, v in data.items():
        if self._something_to_follow(k,v):
          data = self._contract( path=path + [os.path.dirname(v)], data=self._slurp(*path, v), depth = depth+1)
          break
        self._process(recursion={'path':path, 'data':v}, target={'key':k,'data':data}, depth = depth+1)

    # if depth < 3:
    #   print(f"{path} done at depth {depth} (size={self.queue.qsize()})") # , end='\r')

    return data

  def _process(self, *, recursion, target, depth):
    # print(f"Submit request {recursion['path']} : {target['key']} (size={self.queue.qsize()})", end='\r')
    # self.queue.put((recursion, target, depth))
    target['data'][target['key']] = self._contract(path=recursion['path'], data=recursion['data'], depth=depth)

  def _consumer(self, id):
    # print(f"Started consumer {id}", end='\r')
    while not self.event.is_set():
      try:
        recursion, target, depth = self.queue.get(block=True, timeout=1)
        # print(f"Consumer {id} processing message: {recursion['path']} : {target['key']} "
              # f"(size={self.queue.qsize()}) (depth={depth})", end='\r')
        target['data'][target['key']] = self._contract(path=recursion['path'], data=recursion['data'], depth=depth)
      except Exception as e:
          pass

    # print(f"Consumer {id} received event. Exiting.", end='\r')


  def _something_to_follow(self, k, v):

    if k != '$ref':
      return False

    url_details = urlparse(v)
    return not (url_details.scheme or url_details.fragment)

  def _slurp(self, *args):
    with open(os.path.join(*args)) as f:
      return json.load(f)
