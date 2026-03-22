# bioRxiv Search API Summary - Basic Queries

## Content detail
The format of the endpoint is https://api.biorxiv.org/details/[server]/[interval]/[cursor]/[format] or https://api.biorxiv.org/details/[server]/[DOI]/na/[format]

where 'interval' can be 1) two YYYY-MM-DD dates separted by '/' and 'cursor' is the start point which defaults to 0 if not supplied, or 2) a numeric value for the N most recent posts, or 3) a numeric with the letter 'd' for the most recent N days of posts.

Where metadata for multiple papers is returned, results are paginated with 100 papers served in a call. The 'cursor' value can be used to iterate through the result.

For instance, https://api.biorxiv.org/details/biorxiv/2018-08-21/2018-08-28/45 will output 100 results (if that many remain) within the date range of 2018-08-21 to 2018-08-28 beginning from result 45 for biorxiv. https://api.biorxiv.org/details/medrxiv/2020-03-21/2020-03-24/45 will output 100 results (if that many remain) within the date range of 2020-03-21 to 2020-03-24 beginning from result 45 for medrxiv.

These date range endpoints will also accept a querystring paramater for subject category. The subject category can either be URL-encoded or can have underscore substituted for spaces in the category name. For instance, https://api.biorxiv.org/details/biorxiv/2025-03-21/2025-03-28?category=cell_biology will output metadata for Cell Biology for the specified interval and https://api.biorxiv.org/details/medrxiv/2025-03-21/2025-03-28?category=cardiovascular%20medicine will do the same for Cardiovascular Medicine.

https://api.biorxiv.org/details/[server]/[DOI]/na/[format] returns detail for a single manuscript. For instance, https://api.biorxiv.org/details/medrxiv/10.1101/2020.09.09.20191205 will output metadata for the medrxiv paper with DOI 10.1101/339747.

The 'messages' array in the output provides information about what is being displayed, including cursor value, count of all items and count of new papers for the requested interval.

## Available formats:
- JSON (json)
- XML (OAI-PMH XML)
- HTML

## metadata elements returned:


- doi
- title
- authors
- author_corresponding
- author_corresponding_institution
- date
- version
- type
- license
- category
- jats xml path
- abstract
- funding
- name
- id
- id-type
- award
- published
- server

