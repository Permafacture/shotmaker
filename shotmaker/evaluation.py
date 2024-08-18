import random

class FewShotCV:
    def __init__(self, items, query_keys, n=4, seed=42):
        self.items = items
        self.query_keys = query_keys
        self.n = n
        self.seed = seed
        self.rng = random.Random(seed)
        self.index = 0

    def __iter__(self):
        self.index = 0
        self.rng = random.Random(self.seed)
        return self

    def __next__(self):
        if self.index >= len(self.items):
            raise StopIteration

        item = self.items[self.index]
        query = {k: item[k] for k in self.query_keys}
        other_items = self.items[:self.index] + self.items[self.index + 1:]
        shots = self.rng.sample(other_items, min(self.n, len(other_items)))

        self.index += 1
        return query, shots
