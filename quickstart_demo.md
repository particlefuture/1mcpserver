# 

- Set things up according to `README.md`


- generate a website for website SEO analysis: Analyze `builtwith.com`
    - Given website, I want it to 
        - tell me the tech stack: builtwith [https://github.com/builtwith/mcp?tab=readme-ov-file](https://github.com/builtwith/mcp?tab=readme-ov-file`0)
        - extract data (this is nondeterministic, depends on the LLM's mood): 
          - firecrawl [https://github.com/mendableai/firecrawl-mcp-server?tab=readme-ov-file](https://github.com/mendableai/firecrawl-mcp-server?tab=readme-ov-file)
          - webscraping.ai
          - fetch/server-fetch
          - scrapezy

Prompt to Cursor: 
I want to perform analysis of website. I want to be able to analyze the tech stack the website uses, and extract web data. Call the deep_search tool. 