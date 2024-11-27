import sys
from crawler.url_utils import probe_domain

for line in sys.stdin.readlines():
    domain = line.strip()
    print(probe_domain(domain=domain))