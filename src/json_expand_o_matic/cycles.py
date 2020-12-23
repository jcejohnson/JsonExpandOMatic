class CycleDetector:

    def __init__(self, obj):
        self.obj = obj
        self.visited = {}

    def detect(self):

        self._detect(self.obj, [])

    def _detect(self, obj, path):

        if isinstance(obj, dict):
            iterator = obj.items()
        elif isinstance(obj, list):
            iterator = enumerate(obj)
        else:
            return

        self._visit(obj, path)

        for k, v in iterator:
            self._detect(v, path+[k])

    def _detect_list(self, obj):
        self._visit(obj)
        for k, v in enumerate(obj):
            if isinstance(v, dict):
                self._detect_dict(v)
            elif isinstance(v, list):
                self._detect_list(v)

    def _visit(self, obj, path):
        i = id(obj)
        if i in self.visited:
            d = self.visited.get(i)
            raise Exception(f"Circular Reference at id {i} : {path} == {d}")
        self.visited[i] = path
