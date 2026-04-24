#aria/images/observability.py

from collections import defaultdict


from collections import defaultdict


class Metrics:
    def __init__(self):
        self.counters = defaultdict(int)
        self.latencies = defaultdict(list)

    def inc(self, key: str, label: str = "global"):
        self.counters[(key, label)] += 1

    def observe_latency(self, label: str, value: float):
        self.latencies[label].append(value)

    def snapshot(self):
        return {
            "counters": dict(self.counters),
            "latencies": {
                k: {
                    "count": len(v),
                    "avg": sum(v) / len(v) if v else 0
                }
                for k, v in self.latencies.items()
            }
        }


class Logger:
    def log(self, payload: dict):
        print(payload)