from collections import Counter
from dataclasses import dataclass, field
import time
from urllib.parse import urlparse

@dataclass
class ServiceStats:
    docs_in_index: int
    domains_in_index: int
    top3_domains: list[(str, int)]
    start_time: float = time.time()
    avg_latency: float = 0.0
    processed_queries: int = 0
    showed_domains: Counter = field(default_factory=Counter)
    clicked_domains: Counter = field(default_factory=Counter)
    
    def uptime_seconds(self):
        return round(time.time() - self.start_time)
    
    def top_showed_domains(self, n):
        return self.showed_domains.most_common(n)
    
    def top_clicked_domains(self, n):
        return self.clicked_domains.most_common(n)
    
    def update_with_serp(self, showed_urls, latency):
        self.avg_latency = (self.avg_latency * self.processed_queries + latency) / (self.processed_queries + 1)
        self.processed_queries += 1
        for url in showed_urls:
            domain = url.split("/")[2]
            self.showed_domains[domain] += 1
    
    def update_with_click(self, clicked_url):
        domain = urlparse(clicked_url).netloc
        self.clicked_domains[domain] += 1
        
    def stat(self):
        return {
            "docs_in_index": self.docs_in_index,
            "domains_in_index": self.domains_in_index,
            "top3_domains": self.top3_domains,
            "uptime": self.uptime_seconds(),
            "avg_latency": self.avg_latency,
            "top_showed_domains": self.top_showed_domains(3),
            "top_clicked_domains": self.top_clicked_domains(3),
        }