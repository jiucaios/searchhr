"""Run the company profile search demo.

This local demo uses the Serper and Qwen keys hard-coded in company_profile_search.py.

Example:
    python demo_company_profile.py "阿里云" "https://www.aliyun.com" "Python 后端工程师"
"""

from __future__ import annotations

import json
import sys

from company_profile_search import company_profile_search_tool


def main() -> None:
    company_name = sys.argv[1] if len(sys.argv) > 1 else "阿里云"
    company_website = sys.argv[2] if len(sys.argv) > 2 else "https://www.aliyun.com"
    job_description = sys.argv[3] if len(sys.argv) > 3 else "Python 后端工程师"

    result = company_profile_search_tool(
        company_name=company_name,
        company_website=company_website,
        job_description=job_description,
        max_iterations=1,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
